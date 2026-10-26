from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from fshorts.ingest import FrameSampler, Region
from fshorts.reframe.path import CropPath
from fshorts.reframe.upscale import Upscaler


# High quality NVENC settings: slowest preset, constant quality with a generous ceiling and adaptive
# quantisation. The upload is re-encoded by YouTube, so every bit we keep here survives better.
NVENC_QUALITY = [
    "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-maxrate", "30M", "-bufsize", "60M",
    "-spatial-aq", "1", "-temporal-aq", "1", "-bf", "3", "-profile:v", "high",
]
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
    """Cuts a moving window straight out of the match along a crop path: one decode, one encode.

    Layouts on the 9:16 canvas:
      crop - the window is 9:16 itself and fills the screen (tightest, players look biggest);
      wide - a wider window (e.g. 4:5) in the middle over a blurred copy of itself, so the players
             around the ball stay in view and the upscale is smaller (sharper).
    Rendering from the original file, not an already encoded clip, avoids a second generation of compression.
    """

    def __init__(self, sampler: FrameSampler, upscaler: Upscaler, width: int, height: int, encoder: str,
                 bitrate: str, layout: str = "crop", window_aspect: float = 0.8, zoom: float = 1.0,
                 top_margin: float = 0.0, binary: str = "ffmpeg") -> None:
        self._sampler = sampler
        self._upscaler = upscaler
        self._size = (width, height)
        self._encoder = encoder
        self._bitrate = bitrate
        self._layout = layout
        self._aspect = window_aspect if layout == "wide" else width / height
        self._zoom = zoom
        self._top_margin = top_margin
        self._binary = _ffmpeg(binary)

    def window(self, source: tuple[int, int]) -> tuple[int, int, int]:
        """(width, height, top) of the window on the source frame."""
        src_w, src_h = source
        # Keep the broadcaster's score bug strip out of the window; our own overlay replaces it
        top = int(self._top_margin * src_h)
        height = min(int(src_h / self._zoom), src_h - top)
        width = min(src_w, int(round(height * self._aspect)))
        return width, height, top

    def crop_width(self, source_height: int) -> int:
        return self.window((10 ** 6, source_height))[0]

    def render(self, video: Path, start: float, end: float, path: CropPath, source: tuple[int, int], fps: float,
               target: Path) -> Path:
        src_w, src_h = source
        out_w, out_h = self._size
        win_w, win_h, top = self.window(source)
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
                left = int(np.clip(path.center(time) - win_w / 2, 0, src_w - win_w))
                encoder.stdin.write(self._compose(frame[top:top + win_h, left:left + win_w]).tobytes())
        finally:
            encoder.stdin.close()
            encoder.wait()
        if encoder.returncode:
            raise RuntimeError(f"ffmpeg failed on {target.name}")
        return target

    def _compose(self, window: np.ndarray) -> np.ndarray:
        out_w, out_h = self._size
        if self._layout != "wide":
            return self._upscaler.upscale(window, self._size)
        fg_h = int(round(out_w / self._aspect))
        canvas = blurred_cover(window, self._size)
        y = (out_h - fg_h) // 2
        canvas[y:y + fg_h] = self._upscaler.upscale(window, (out_w, fg_h))
        return canvas


def blurred_cover(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """The image scaled to cover `size`, centre-cropped, blurred and darkened (blurred small, so it is cheap)."""
    out_w, out_h = size
    h, w = image.shape[:2]
    scale = max(out_w / w, out_h / h)
    small = cv2.resize(image, (max(1, int(w * scale / 8)), max(1, int(h * scale / 8))), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    big = cv2.resize(small, (int(w * scale) + 1, int(h * scale) + 1), interpolation=cv2.INTER_LINEAR)
    x, y = (big.shape[1] - out_w) // 2, (big.shape[0] - out_h) // 2
    return (big[y:y + out_h, x:x + out_w] * 0.6).astype(np.uint8)


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
