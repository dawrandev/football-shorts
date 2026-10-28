from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from fshorts.branding.text import FONT_BLACK, FONT_BOLD, TextPainter, rounded_box, to_array

# What the badge says at the moment itself, per replay label
BADGES = {
    "goal": "GOAL!", "shot_saved": "WHAT A SAVE", "near_miss": "SO CLOSE", "woodwork": "OFF THE POST",
    "shot_off_target": "JUST WIDE", "shot_blocked": "BLOCKED", "skill": "SKILLS",
}
HOOK_SHARE = 0.45          # the reference Shorts show their hook for the first ~45%
FADE = 0.25
BADGE_SECONDS = 1.8
POP_SECONDS = 0.22
ACCENT = (255, 212, 0, 255)


@dataclass(frozen=True)
class OverlaySpec:
    home: str
    away: str
    score_before: tuple[int, int]
    score_after: tuple[int, int]
    minute: int | None
    moment: float              # seconds from the start of the Short
    duration: float
    badge: str
    hook: str
    caption: str               # shown in the lower band after the moment, e.g. "Richarlison 31'"


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
    """Score bar, hook, moment badge and caption drawn over each frame of a 1080x1920 Short.

    Built once per clip (text is rasterised up front); per frame only alpha blending is left.
    """

    def __init__(self, spec: OverlaySpec, size: tuple[int, int], window_top: int, window_bottom: int) -> None:
        self._spec = spec
        width, height = size
        top_band = max(window_top, 160)
        bottom_mid = (window_bottom + height) // 2 if height - window_bottom > 120 else height - 170
        self._score_before = Layer(self._score_bar(spec.score_before), (width // 2, top_band // 2 + 10))
        self._score_after = Layer(self._score_bar(spec.score_after, highlight=True), (width // 2, top_band // 2 + 10))
        self._hook = self._text(spec.hook, 58, width, bottom_mid)
        self._caption = self._text(spec.caption, 50, width, bottom_mid)
        self._badge = Layer(self._badge_box(spec.badge), (width // 2, window_bottom - 150)) if spec.badge else None

    def apply(self, canvas: np.ndarray, time: float) -> np.ndarray:
        spec = self._spec
        changed = spec.score_after != spec.score_before and time >= spec.moment
        (self._score_after if changed else self._score_before).blend(canvas, 1.0)
        if self._hook is not None:
            self._hook.blend(canvas, _window(time, 0.2, spec.duration * HOOK_SHARE))
        since = time - spec.moment
        if self._badge is not None and 0 <= since <= BADGE_SECONDS:
            pop = min(1.0, 0.6 + 0.4 * since / POP_SECONDS)
            self._badge.blend(canvas, _window(since, 0.0, BADGE_SECONDS), scale=pop)
        if self._caption is not None and since >= 0:
            self._caption.blend(canvas, min(1.0, since / FADE))
        return canvas

    @staticmethod
    def _text(text: str, size: int, width: int, y: int) -> Layer | None:
        return Layer(TextPainter(size).render(text, width - 120), (width // 2, y)) if text else None

    def _score_bar(self, score: tuple[int, int], highlight: bool = False) -> Image.Image:
        spec = self._spec
        teams = TextPainter(52, FONT_BOLD, shadow=False)
        digits = TextPainter(60, FONT_BLACK, color=ACCENT if highlight else (255, 255, 255, 255), shadow=False)
        parts = [teams.render(spec.home, 400), digits.render(f"{score[0]} - {score[1]}", 400),
                 teams.render(spec.away, 400)]
        if spec.minute is not None:
            parts.append(TextPainter(40, FONT_BOLD, color=(200, 200, 200, 255), shadow=False)
                         .render(f"{spec.minute}'", 200))
        gap = 18
        width = sum(p.width for p in parts) + gap * (len(parts) - 1) + 60
        height = max(p.height for p in parts) + 20
        bar = rounded_box((width, height), height // 2, (12, 12, 16, 200))
        x = 30
        for part in parts:
            bar.alpha_composite(part, (x, (height - part.height) // 2))
            x += part.width + gap
        return bar

    @staticmethod
    def _badge_box(text: str) -> Image.Image:
        label = TextPainter(76, FONT_BLACK, color=(16, 16, 16, 255), shadow=False).render(text, 1000)
        box = rounded_box((label.width + 70, label.height + 20), 28, ACCENT)
        box.alpha_composite(label, (35, 10))
        return box


def _window(time: float, start: float, end: float) -> float:
    """Opacity of something shown from start to end with short fades."""
    if time < start or time > end:
        return 0.0
    return min(1.0, (time - start) / FADE, (end - time) / FADE)
