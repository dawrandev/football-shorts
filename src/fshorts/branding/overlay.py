from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np
from PIL import Image

from fshorts.branding.text import TextPainter, to_array

FADE = 0.2
# Captions are on from the first frame and leave just before the moment they tease
LEAD_IN = 0.0
REVEAL_GAP = 0.25
MIN_LABEL_SECONDS = 3.0


@dataclass(frozen=True)
class CaptionStyle:
    """Where and how big the caption sits, measured on the most viewed reference Shorts."""

    size: int = 56            # font size in px on the 1080x1920 canvas
    y_share: float = 0.70     # vertical centre of the caption, share of the canvas height
    label_share: float = 0.5  # a label stays up for this share of the live part


@dataclass(frozen=True)
class OverlaySpec:
    format: str                # label, teaser, question or two_beat
    line1: str
    line2: str | None
    moment: float              # seconds from the start of this part of the Short
    duration: float

    def for_replay(self, duration: float) -> OverlaySpec:
        """The replay angle at the end runs clean, like the reference Shorts."""
        return replace(self, line1="", line2=None, moment=0.0, duration=duration)


class Layer:
    def __init__(self, image: Image.Image, center: tuple[int, int]) -> None:
        self.rgba = to_array(image)
        self.center = center

    def blend(self, canvas: np.ndarray, opacity: float, scale: float = 1.0) -> None:
        if opacity <= 0:
            return
        rgba = self.rgba
        if scale != 1.0:
            rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        h, w = rgba.shape[:2]
        x, y = self.center[0] - w // 2, self.center[1] - h // 2
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, canvas.shape[1]), min(y + h, canvas.shape[0])
        if x1 <= x0 or y1 <= y0:
            return
        part = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
        alpha = part[..., 3:4] / 255.0 * opacity
        region = canvas[y0:y1, x0:x1].astype(np.float32)
        canvas[y0:y1, x0:x1] = (region * (1 - alpha) + part[..., :3] * alpha).astype(np.uint8)


class ShortOverlay:
    """One short white caption on the video itself, the way the big channels caption their Shorts.

    No score bar and no badge: the most viewed Shorts have neither. Text is rasterised once per clip;
    per frame only alpha blending is left.
    """

    def __init__(self, spec: OverlaySpec, size: tuple[int, int], style: CaptionStyle = CaptionStyle()) -> None:
        self._spec = spec
        self._style = style
        width, height = size
        y = int(style.y_share * height)
        self._line1 = self._text(spec.line1, width, y)
        self._line2 = self._text(spec.line2, width, y) if spec.line2 else None

    def windows(self) -> list[tuple[str, float, float]]:
        """(line, from, to) in seconds of this part."""
        spec, style = self._spec, self._style
        found = []
        if spec.line1:
            if spec.format == "label" and not spec.line2:
                end = max(spec.duration * style.label_share, MIN_LABEL_SECONDS)
            else:
                end = spec.moment - REVEAL_GAP
            found.append(("line1", LEAD_IN, min(end, spec.duration)))
        if spec.line2:
            found.append(("line2", spec.moment, spec.duration))
        return [w for w in found if w[2] > w[1]]

    def apply(self, canvas: np.ndarray, time: float) -> np.ndarray:
        for name, start, end in self.windows():
            layer = self._line1 if name == "line1" else self._line2
            if layer is not None:
                layer.blend(canvas, _window(time, start, end))
        return canvas

    def _text(self, text: str, width: int, y: int) -> Layer | None:
        return Layer(TextPainter(self._style.size).render(text, int(width * 0.84)), (width // 2, y)) if text else None


def _window(time: float, start: float, end: float) -> float:
    """Opacity of something shown from start to end with short fades."""
    if time < start or time > end:
        return 0.0
    return min(1.0, (time - start) / FADE, (end - time) / FADE)
