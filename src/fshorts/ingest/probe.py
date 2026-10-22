from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoInfo:
    path: Path
    duration_seconds: float
    width: int
    height: int
    fps: float
    video_codec: str
    has_audio: bool

    @property
    def duration_label(self) -> str:
        total = int(self.duration_seconds)
        return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


class FfprobeProber:
    """Reads stream metadata of a video file through ffprobe."""

    def __init__(self, binary: str = "ffprobe") -> None:
        resolved = shutil.which(binary)
        if resolved is None:
            raise ProbeError(f"'{binary}' not found on PATH")
        self._binary = resolved

    def probe(self, path: Path) -> VideoInfo:
        if not path.is_file():
            raise ProbeError(f"file not found: {path}")
        data = self._run(path)
        video = self._first_stream(data, "video")
        if video is None:
            raise ProbeError(f"no video stream in {path}")
        return VideoInfo(
            path=path,
            duration_seconds=float(data["format"]["duration"]),
            width=int(video["width"]),
            height=int(video["height"]),
            fps=float(Fraction(video["avg_frame_rate"])),
            video_codec=video["codec_name"],
            has_audio=self._first_stream(data, "audio") is not None,
        )

    def _run(self, path: Path) -> dict:
        command = [
            self._binary, "-v", "error",
            "-show_format", "-show_streams",
            "-of", "json", str(path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise ProbeError(result.stderr.strip() or f"ffprobe failed on {path}")
        return json.loads(result.stdout)

    @staticmethod
    def _first_stream(data: dict, codec_type: str) -> dict | None:
        return next(
            (s for s in data.get("streams", []) if s.get("codec_type") == codec_type),
            None,
        )
