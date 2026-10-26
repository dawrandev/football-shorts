from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from fshorts.broadcast import BroadcastTimeline
from fshorts.ingest import FrameSampler, Region
from fshorts.reframe.detection import RfDetrDetector
from fshorts.reframe.path import BallTracker

TILE = 640


@dataclass(frozen=True)
class BallLabel:
    time: float
    box: tuple[float, float, float, float]   # x1, y1, x2, y2 on the full frame
    score: float                             # detector confidence; weak ones were confirmed by the track


class BallPseudoLabeler:
    """Self-training labels for our own ball detector, no hand labelling needed.

    The tiled pretrained detector plus the track find the ball; a weak detection that sits on the
    track is a label the new model should learn to be sure about. Windows come only from live,
    wide play so the labels match what the reframer has to follow.
    """

    def __init__(self, sampler: FrameSampler, detector: RfDetrDetector, fps: float = 10.0,
                 window_seconds: float = 6.0, every_seconds: float = 30.0, min_live: float = 0.8) -> None:
        self._sampler = sampler
        self._detector = detector
        self._fps = fps
        self._window = window_seconds
        self._every = every_seconds
        self._min_live = min_live

    def windows(self, timeline: BroadcastTimeline, duration: float) -> list[float]:
        starts = []
        for start in np.arange(0.0, duration - self._window, self._every):
            times = np.arange(start, start + self._window, 1.0)
            if np.mean([timeline.is_live_play(t) for t in times]) >= self._min_live:
                starts.append(float(start))
        return starts

    def label(self, video: Path, start: float, size: tuple[int, int]) -> list[tuple[np.ndarray, BallLabel]]:
        tracker = BallTracker(size[0])
        found = []
        frames = self._sampler.sample(video, self._fps, Region(0, 0, *size), start=start, duration=self._window)
        for time, frame in frames:
            balls = self._detector.balls(frame)
            x = tracker.update(time, balls)
            if x is None:
                continue
            centers = (balls[:, 0] + balls[:, 2]) / 2
            box = balls[np.abs(centers - x).argmin()]
            found.append((frame, BallLabel(start + time, tuple(float(v) for v in box[:4]), float(box[4]))))
        return found


class CocoTileWriter:
    """Writes 640x640 tiles in the COCO layout RF-DETR trains on: one tile around the ball, one without it."""

    def __init__(self, root: Path, seed: int = 0) -> None:
        self._root = root
        self._random = random.Random(seed)
        self._splits: dict[str, dict] = {}

    def add(self, split: str, name: str, frame: np.ndarray, label: BallLabel) -> None:
        data = self._splits.setdefault(split, {"images": [], "annotations": [],
                                               "categories": [{"id": 0, "name": "ball", "supercategory": "none"}]})
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = label.box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        # Positive: the ball anywhere inside the tile, not always in the middle
        left = int(np.clip(cx - self._random.uniform(0.15, 0.85) * TILE, 0, width - TILE))
        top = int(np.clip(cy - self._random.uniform(0.15, 0.85) * TILE, 0, height - TILE))
        self._write(data, split, f"{name}_p", frame, left, top, [(x1 - left, y1 - top, x2 - x1, y2 - y1)])
        # Negative: a tile far from the ball; there is only one ball on the pitch
        for _ in range(10):
            left = self._random.randint(0, width - TILE)
            top = self._random.randint(0, height - TILE)
            if not (left - 50 <= cx <= left + TILE + 50 and top - 50 <= cy <= top + TILE + 50):
                self._write(data, split, f"{name}_n", frame, left, top, [])
                break

    def _write(self, data: dict, split: str, name: str, frame: np.ndarray, left: int, top: int, boxes) -> None:
        folder = self._root / split
        folder.mkdir(parents=True, exist_ok=True)
        file = f"{name}.jpg"
        tile = frame[top:top + TILE, left:left + TILE]
        cv2.imwrite(str(folder / file), cv2.cvtColor(tile, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
        image_id = len(data["images"])
        data["images"].append({"id": image_id, "file_name": file, "width": TILE, "height": TILE})
        for x, y, w, h in boxes:
            data["annotations"].append({"id": len(data["annotations"]), "image_id": image_id, "category_id": 0,
                                        "bbox": [x, y, w, h], "area": w * h, "iscrowd": 0})

    def close(self) -> dict[str, int]:
        for split, data in self._splits.items():
            (self._root / split / "_annotations.coco.json").write_text(json.dumps(data), encoding="utf-8")
        return {split: len(data["images"]) for split, data in self._splits.items()}
