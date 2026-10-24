from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# COCO class ids of the pretrained detector
PERSON, SPORTS_BALL = 1, 37


@dataclass(frozen=True)
class FrameDetections:
    """Boxes of one frame as rows of (x1, y1, x2, y2, score) in source pixels."""

    time: float
    players: np.ndarray
    balls: np.ndarray

    def to_dict(self) -> dict:
        return {"time": self.time, "players": self.players.round(1).tolist(), "balls": self.balls.round(3).tolist()}

    @classmethod
    def from_dict(cls, raw: dict) -> FrameDetections:
        return cls(raw["time"], _boxes(raw["players"]), _boxes(raw["balls"]))


def _boxes(rows) -> np.ndarray:
    return np.asarray(rows, dtype=np.float32).reshape(-1, 5)


class ObjectDetector(ABC):
    @abstractmethod
    def detect(self, frames: list[np.ndarray]) -> list[tuple[np.ndarray, np.ndarray]]:
        """(players, balls) box arrays per RGB frame."""


class RfDetrDetector(ObjectDetector):
    """Pretrained RF-DETR Medium (Apache-2.0) in fp16; players are reliable, the small ball is not yet."""

    def __init__(self, threshold: float = 0.3, batch_size: int = 8) -> None:
        import torch
        from rfdetr import RFDETRMedium

        self._model = RFDETRMedium()
        self._model.inference(batch_size=batch_size, dtype=torch.float16)
        self._threshold = threshold
        self._batch = batch_size

    def detect(self, frames: list[np.ndarray]) -> list[tuple[np.ndarray, np.ndarray]]:
        results = []
        for i in range(0, len(frames), self._batch):
            chunk = frames[i:i + self._batch]
            padded = chunk + [chunk[-1]] * (self._batch - len(chunk))   # the optimised model wants full batches
            for d in self._model.predict(padded, threshold=self._threshold)[:len(chunk)]:
                rows = np.column_stack([d.xyxy, d.confidence]).astype(np.float32)
                results.append((rows[d.class_id == PERSON], rows[d.class_id == SPORTS_BALL]))
        return results


class CachedDetections:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[FrameDetections] | None:
        if not self._path.is_file():
            return None
        return [FrameDetections.from_dict(d) for d in json.loads(self._path.read_text(encoding="utf-8"))]

    def save(self, detections: list[FrameDetections]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([d.to_dict() for d in detections]), encoding="utf-8")
