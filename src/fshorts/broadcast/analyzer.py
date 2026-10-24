from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fshorts.broadcast.bug import ScoreBugDetector
from fshorts.broadcast.timeline import BroadcastTimeline
from fshorts.broadcast.views import ViewClassifier
from fshorts.ingest import FrameSampler, Region
from fshorts.scoreboard import ScoreReading

# Frames are analysed at this size; the bug region is given on a 1920x1080 frame
FRAME_SIZE = (384, 216)
BATCH = 256


class BroadcastAnalyzer:
    """One low-resolution decode of the match -> score bug visibility and camera view per frame."""

    def __init__(self, sampler: FrameSampler, views: ViewClassifier, bug: ScoreBugDetector, fps: float = 2.0) -> None:
        self._sampler = sampler
        self._views = views
        self._bug = bug
        self._fps = fps

    def analyze(self, video: Path, bug_region: Region, readings: list[ScoreReading]) -> BroadcastTimeline:
        full = Region(0, 0, 1920, 1080)
        scale = FRAME_SIZE[0] / full.width
        x0, y0 = int(bug_region.x * scale), int(bug_region.y * scale)
        x1, y1 = x0 + int(bug_region.width * scale), y0 + int(bug_region.height * scale)
        crops, views, batch = [], [], []
        for _, frame in self._sampler.sample(video, self._fps, full, size=FRAME_SIZE):
            crops.append(frame[y0:y1, x0:x1].mean(axis=2).astype(np.uint8))
            batch.append(frame)
            if len(batch) == BATCH:
                views += self._views.classify(batch)
                batch = []
        if batch:
            views += self._views.classify(batch)
        stack = np.stack(crops)
        read = np.zeros(len(stack), dtype=bool)
        for r in readings:
            i = int(round(r.time * self._fps))
            if i < len(read):
                read[i] = True
        self._bug.fit(stack, read)
        return BroadcastTimeline(self._fps, tuple(bool(v) for v in self._bug.visible(stack)), tuple(views))


class CachedBroadcastAnalyzer:
    def __init__(self, inner: BroadcastAnalyzer, cache: Path) -> None:
        self._inner = inner
        self._cache = cache

    def analyze(self, video: Path, bug_region: Region, readings: list[ScoreReading]) -> BroadcastTimeline:
        if self._cache.is_file():
            return BroadcastTimeline.from_dict(json.loads(self._cache.read_text(encoding="utf-8")))
        timeline = self._inner.analyze(video, bug_region, readings)
        self._cache.write_text(json.dumps(timeline.to_dict()), encoding="utf-8")
        return timeline
