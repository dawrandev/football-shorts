from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from fshorts.ingest import FrameSampler, Region
from fshorts.reframe.path import CropPath


def _ffmpeg(binary: str) -> str:
    resolved = shutil.which(binary)
    if resolved is None:
        raise RuntimeError(f"'{binary}' not found on PATH")
    return resolved


class VerticalCropRenderer:
    """Cuts a moving 9:16 window out of a 16:9 clip along a crop path and encodes it on the GPU."""

    def __init__(self, sampler: FrameSampler, width: int, height: int, encoder: str, bitrate: str,
                 zoom: float = 1.0, top_margin: float = 0.0, binary: str = "ffmpeg") -> None:
        self._sampler = sampler
        self._size = (width, height)
        self._encoder = encoder
        self._bitrate = bitrate
        self._zoom = zoom
        self._top_margin = top_margin
        self._binary = _ffmpeg(binary)

    def render(self, clip: Path, path: CropPath, source: tuple[int, int], fps: float, target: Path) -> Path:
        src_w, src_h = source
        out_w, out_h = self._size
        crop_h = int(src_h / self._zoom)
        crop_w = int(round(crop_h * out_w / out_h))
        # Keep the broadcaster's score bug strip out of the window; our own overlay replaces it
        top = min(src_h - crop_h, max((src_h - crop_h) // 2, int(self._top_margin * src_h)))
        encoder = subprocess.Popen([
            self._binary, "-v", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{out_w}x{out_h}", "-r", f"{fps}", "-i", "-",
            "-i", str(clip), "-map", "0:v", "-map", "1:a?",
            "-c:v", self._encoder, "-b:v", self._bitrate, "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(target),
        ], stdin=subprocess.PIPE)
        try:
            for time, frame in self._sampler.sample(clip, fps, Region(0, 0, src_w, src_h)):
                left = int(np.clip(path.center(time) - crop_w / 2, 0, src_w - crop_w))
                window = frame[top:top + crop_h, left:left + crop_w]
                encoder.stdin.write(cv2.resize(window, self._size, interpolation=cv2.INTER_CUBIC).tobytes())
        finally:
            encoder.stdin.close()
            encoder.wait()
        if encoder.returncode:
            raise RuntimeError(f"ffmpeg failed on {target.name}")
        return target


class BlurFitRenderer:
    """Fallback when nothing can be followed: the whole 16:9 frame over a blurred, zoomed copy of itself."""

    def __init__(self, width: int, height: int, encoder: str, bitrate: str, binary: str = "ffmpeg") -> None:
        self._size = (width, height)
        self._encoder = encoder
        self._bitrate = bitrate
        self._binary = _ffmpeg(binary)

    def render(self, clip: Path, target: Path) -> Path:
        w, h = self._size
        graph = (
            f"[0:v]split[a][b];[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"boxblur=24:2[bg];[b]scale={w}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        subprocess.run([
            self._binary, "-v", "error", "-y", "-i", str(clip), "-filter_complex", graph,
            "-c:v", self._encoder, "-b:v", self._bitrate, "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart", str(target),
        ], check=True)
        return target
