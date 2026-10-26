from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from fshorts.ingest import FrameSampler, Region
from fshorts.reframe.path import CropPath


# High quality NVENC settings: slowest preset, constant quality with a generous ceiling and adaptive
# quantisation. The upload is re-encoded by YouTube, so every bit we keep here survives better.
NVENC_QUALITY = [
    "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-maxrate", "30M", "-bufsize", "60M",
    "-spatial-aq", "1", "-temporal-aq", "1", "-bf", "3", "-profile:v", "high",
]
# Upscaled crops look soft; a light unsharp mask restores edges without halos
SHARPEN_AMOUNT = 0.5
SHARPEN_SIGMA = 1.2


def encoder_options(encoder: str, bitrate: str) -> list[str]:
    if encoder.endswith("_nvenc"):
        return ["-c:v", encoder, "-b:v", bitrate, *NVENC_QUALITY]
    return ["-c:v", encoder, "-b:v", bitrate]


def _ffmpeg(binary: str) -> str:
    resolved = shutil.which(binary)
    if resolved is None:
        raise RuntimeError(f"'{binary}' not found on PATH")
    return resolved


class VerticalCropRenderer:
    """Cuts a moving 9:16 window straight out of the match along a crop path: one decode, one encode.

    Rendering from the original file (not from an already encoded clip) avoids a second generation
    of compression; Lanczos scaling plus a light unsharp mask keeps the ~2x upscale crisp.
    """

    def __init__(self, sampler: FrameSampler, width: int, height: int, encoder: str, bitrate: str,
                 zoom: float = 1.0, top_margin: float = 0.0, binary: str = "ffmpeg") -> None:
        self._sampler = sampler
        self._size = (width, height)
        self._encoder = encoder
        self._bitrate = bitrate
        self._zoom = zoom
        self._top_margin = top_margin
        self._binary = _ffmpeg(binary)

    def crop_width(self, source_height: int) -> int:
        out_w, out_h = self._size
        return int(round(int(source_height / self._zoom) * out_w / out_h))

    def render(self, video: Path, start: float, end: float, path: CropPath, source: tuple[int, int], fps: float,
               target: Path) -> Path:
        src_w, src_h = source
        out_w, out_h = self._size
        crop_h = int(src_h / self._zoom)
        crop_w = int(round(crop_h * out_w / out_h))
        # Keep the broadcaster's score bug strip out of the window; our own overlay replaces it
        top = min(src_h - crop_h, max((src_h - crop_h) // 2, int(self._top_margin * src_h)))
        encoder = subprocess.Popen([
            self._binary, "-v", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{out_w}x{out_h}", "-r", f"{fps}", "-i", "-",
            "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(video), "-map", "0:v", "-map", "1:a?",
            *encoder_options(self._encoder, self._bitrate), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(target),
        ], stdin=subprocess.PIPE)
        try:
            frames = self._sampler.sample(video, fps, Region(0, 0, src_w, src_h), start=start, duration=end - start)
            for time, frame in frames:
                left = int(np.clip(path.center(time) - crop_w / 2, 0, src_w - crop_w))
                window = frame[top:top + crop_h, left:left + crop_w]
                encoder.stdin.write(self._upscale(window).tobytes())
        finally:
            encoder.stdin.close()
            encoder.wait()
        if encoder.returncode:
            raise RuntimeError(f"ffmpeg failed on {target.name}")
        return target


    def _upscale(self, window: np.ndarray) -> np.ndarray:
        scaled = cv2.resize(window, self._size, interpolation=cv2.INTER_LANCZOS4)
        blurred = cv2.GaussianBlur(scaled, (0, 0), SHARPEN_SIGMA)
        return cv2.addWeighted(scaled, 1 + SHARPEN_AMOUNT, blurred, -SHARPEN_AMOUNT, 0)


class BlurFitRenderer:
    """Fallback when nothing can be followed: the whole 16:9 frame over a blurred, zoomed copy of itself."""

    def __init__(self, width: int, height: int, encoder: str, bitrate: str, binary: str = "ffmpeg") -> None:
        self._size = (width, height)
        self._encoder = encoder
        self._bitrate = bitrate
        self._binary = _ffmpeg(binary)

    def render(self, video: Path, start: float, end: float, target: Path) -> Path:
        w, h = self._size
        graph = (
            f"[0:v]split[a][b];[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"boxblur=24:2[bg];[b]scale={w}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        subprocess.run([
            self._binary, "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(video),
            "-filter_complex", graph, *encoder_options(self._encoder, self._bitrate), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target),
        ], check=True)
        return target
