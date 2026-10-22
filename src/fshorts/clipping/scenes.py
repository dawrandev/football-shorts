from __future__ import annotations

import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from fshorts.clipping.planner import ClipPlan

SCD_TIME = re.compile(r"lavfi\.scd\.time:\s*([0-9.]+)")


class SceneCutDetector(ABC):
    @abstractmethod
    def cuts(self, video: Path, start: float, end: float) -> list[float]:
        """Camera cut times (seconds from file start) inside [start, end]."""


class FfmpegSceneCutDetector(SceneCutDetector):
    """ffmpeg's scdet filter on a downscaled copy of the window; no extra dependency."""

    def __init__(self, threshold: float = 10.0, binary: str = "ffmpeg") -> None:
        resolved = shutil.which(binary)
        if resolved is None:
            raise RuntimeError(f"'{binary}' not found on PATH")
        self._binary = resolved
        self._threshold = threshold

    def cuts(self, video: Path, start: float, end: float) -> list[float]:
        command = [
            self._binary, "-v", "info", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(video),
            "-vf", f"scale=320:-1,scdet=threshold={self._threshold}", "-an", "-f", "null", "-",
        ]
        result = subprocess.run(command, capture_output=True, text=True, errors="replace")
        return [start + float(m) for m in SCD_TIME.findall(result.stderr)]


class SceneSnapper:
    """Moves clip edges onto nearby camera cuts so a clip never opens or ends mid-shot."""

    def __init__(self, detector: SceneCutDetector, snap_seconds: float) -> None:
        self._detector = detector
        self._snap = snap_seconds

    def snap(self, video: Path, plan: ClipPlan) -> ClipPlan:
        cuts = self._detector.cuts(video, max(0.0, plan.start - self._snap), plan.end + self._snap)
        # Start may only move earlier (keep the build-up), end only later (keep the finish)
        start = max((c for c in cuts if plan.start - self._snap <= c <= plan.start), default=plan.start)
        end = min((c for c in cuts if plan.end <= c <= plan.end + self._snap), default=plan.end)
        return ClipPlan(plan.kind, plan.anchor, start, end, plan.score, plan.label)
