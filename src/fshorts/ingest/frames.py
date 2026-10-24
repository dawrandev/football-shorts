from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Region:
    x: int
    y: int
    width: int
    height: int


class FrameSampler:
    """Streams cropped RGB frames at a fixed rate from one ffmpeg decode (NVDEC when available)."""

    def __init__(self, binary: str = "ffmpeg", hwaccel: str | None = "cuda") -> None:
        resolved = shutil.which(binary)
        if resolved is None:
            raise RuntimeError(f"'{binary}' not found on PATH")
        self._binary = resolved
        self._hwaccel = hwaccel

    def sample(
        self, video: Path, fps: float, region: Region, size: tuple[int, int] | None = None, gray: bool = False
    ) -> Iterator[tuple[float, np.ndarray]]:
        """Yields (time, frame); `size` rescales the crop to (width, height), `gray` returns one channel."""
        width, height = size or (region.width, region.height)
        channels = 1 if gray else 3
        scale = f",scale={width}:{height}" if size else ""
        command = [self._binary, "-v", "error"]
        if self._hwaccel:
            command += ["-hwaccel", self._hwaccel]
        command += [
            "-i", str(video),
            "-vf", f"fps={fps},crop={region.width}:{region.height}:{region.x}:{region.y}{scale}",
            "-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24", "-",
        ]
        frame_bytes = width * height * channels
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            index = 0
            while chunk := process.stdout.read(frame_bytes):
                if len(chunk) < frame_bytes:
                    break
                shape = (height, width) if gray else (height, width, 3)
                frame = np.frombuffer(chunk, np.uint8).reshape(shape)
                yield index / fps, frame
                index += 1
        finally:
            process.stdout.close()
            process.wait()
