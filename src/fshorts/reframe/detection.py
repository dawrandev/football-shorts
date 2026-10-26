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
    """Pretrained RF-DETR Medium (Apache-2.0): players on the whole frame, the ball on overlapping tiles.

    The model sees a 576 px image; a whole 1080p frame shrinks the 10-15 px ball to a few pixels,
    so the ball is searched in a 3x2 grid of tiles at nearly native size (75% -> 92% of frames).
    """

    def __init__(self, threshold: float = 0.3, ball_threshold: float = 0.25, tiles: tuple[int, int] = (3, 2),
                 overlap: int = 64, ball_weights: Path | None = None) -> None:
        from rfdetr import RFDETRMedium

        self._model = RFDETRMedium()
        # Our own single-class ball model, fine-tuned on pseudo-labelled tiles (fshorts trainball)
        self._ball_model = RFDETRMedium(pretrain_weights=str(ball_weights), resolution=640) if ball_weights else None
        self._ball_class = 0 if ball_weights else SPORTS_BALL
        self._threshold = threshold
        self._ball_threshold = ball_threshold
        self._tiles = tiles
        self._overlap = overlap

    def detect(self, frames: list[np.ndarray]) -> list[tuple[np.ndarray, np.ndarray]]:
        return [(self._players(frame), self.balls(frame)) for frame in frames]

    def _rows(self, detections, class_id: int) -> np.ndarray:
        rows = np.column_stack([detections.xyxy, detections.confidence]).astype(np.float32)
        return rows[detections.class_id == class_id]

    def _players(self, frame: np.ndarray) -> np.ndarray:
        return self._rows(self._model.predict(frame, threshold=self._threshold), PERSON)

    def balls(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        cols, rows = self._tiles
        tiles, offsets = [], []
        for r in range(rows):
            for c in range(cols):
                x0, y0 = max(0, c * width // cols - self._overlap), max(0, r * height // rows - self._overlap)
                x1 = min(width, (c + 1) * width // cols + self._overlap)
                y1 = min(height, (r + 1) * height // rows + self._overlap)
                tiles.append(frame[y0:y1, x0:x1])
                offsets.append((x0, y0))
        found = []
        model = self._ball_model or self._model
        for detections, (x0, y0) in zip(model.predict(tiles, threshold=self._ball_threshold), offsets):
            balls = self._rows(detections, self._ball_class)
            balls[:, [0, 2]] += x0
            balls[:, [1, 3]] += y0
            found.append(balls)
        return merge_duplicates(np.concatenate(found))


def merge_duplicates(boxes: np.ndarray, distance: float = 15.0) -> np.ndarray:
    """One box per object where overlapping tiles both saw it: keep the most confident."""
    kept: list[np.ndarray] = []
    for box in boxes[np.argsort(-boxes[:, 4])]:
        center = (box[:2] + box[2:4]) / 2
        if all(np.linalg.norm(center - (k[:2] + k[2:4]) / 2) > distance for k in kept):
            kept.append(box)
    return np.array(kept, dtype=np.float32).reshape(-1, 5)


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
