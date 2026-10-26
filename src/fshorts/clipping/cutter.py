from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from fshorts.clipping.planner import ClipPlan
from fshorts.reframe.render import encoder_options


class ClipCutter:
    """Frame-accurate cut with a GPU re-encode; stream copy would snap to keyframes seconds away."""

    def __init__(self, encoder: str, bitrate: str, binary: str = "ffmpeg") -> None:
        resolved = shutil.which(binary)
        if resolved is None:
            raise RuntimeError(f"'{binary}' not found on PATH")
        self._binary = resolved
        self._encoder = encoder
        self._bitrate = bitrate

    def cut(self, video: Path, plan: ClipPlan, target: Path) -> Path:
        command = [
            self._binary, "-v", "error", "-y",
            "-ss", f"{plan.start:.3f}", "-t", f"{plan.duration:.3f}", "-i", str(video),
            *encoder_options(self._encoder, self._bitrate), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target),
        ]
        subprocess.run(command, check=True)
        return target
