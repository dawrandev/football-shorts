from __future__ import annotations

from pathlib import Path

import numpy as np

from fshorts.broadcast.timeline import Replay
from fshorts.ingest import FrameSampler, Region

THUMB_SIZE = (64, 36)


class RecapDetector:
    """Finds replays that re-air footage shown earlier (half-time recaps, "the first goal again").

    New replays show new camera angles; a recap is pixel-for-pixel the same frames, so tiny
    normalised thumbnails match almost perfectly while unrelated football frames do not.
    """

    def __init__(self, sampler: FrameSampler, fps: float = 2.0, min_similarity: float = 0.95,
                 min_fraction: float = 0.3, gap_seconds: float = 60.0) -> None:
        self._sampler = sampler
        self._fps = fps
        self._min_similarity = min_similarity
        self._min_fraction = min_fraction
        self._gap = gap_seconds

    def thumbnails(self, video: Path) -> np.ndarray:
        frames = [f for _, f in self._sampler.sample(video, self._fps, Region(0, 0, 1920, 1080),
                                                     size=THUMB_SIZE, gray=True)]
        flat = np.stack(frames).reshape(len(frames), -1).astype(np.float32)
        flat -= flat.mean(axis=1, keepdims=True)
        return flat / (np.linalg.norm(flat, axis=1, keepdims=True) + 1e-6)

    def recaps(self, thumbs: np.ndarray, replays: list[Replay]) -> list[bool]:
        return [self._is_recap(thumbs, r) for r in replays]

    def _is_recap(self, thumbs: np.ndarray, replay: Replay) -> bool:
        a, b = int(replay.start * self._fps), int(replay.end * self._fps)
        earlier = thumbs[: max(0, a - int(self._gap * self._fps))]
        if len(earlier) == 0 or b <= a:
            return False
        best = (thumbs[a:b] @ earlier.T).max(axis=1)
        return float((best >= self._min_similarity).mean()) >= self._min_fraction
