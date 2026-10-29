from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_BLACK = "C:/Windows/Fonts/seguibl.ttf"
FONT_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"
# Emoji and pictographs (with joiners and variation selectors) go to the colour emoji font
EMOJI = re.compile("([\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF][\uFE0F\u200D\U0001F000-\U0001FAFF]*)")


@lru_cache(maxsize=32)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(FONT_BOLD, size)


class TextPainter:
    """Draws one or more lines of text mixed with colour emoji onto a transparent RGBA image."""

    def __init__(self, size: int, face: str = FONT_BOLD, color=(255, 255, 255, 255), shadow: bool = True) -> None:
        self._text_font = font(face, size)
        self._emoji_font = font(FONT_EMOJI, int(size * 0.9))
        self._color = color
        self._shadow = shadow
        self._size = size

    def wrap(self, text: str, max_width: int) -> list[str]:
        """Greedy wrap, then narrowed as far as the line count allows so no word is left alone."""
        lines = self._greedy(text, max_width)
        low, high = 1, max_width
        while len(lines) > 1 and low < high:
            middle = (low + high) // 2
            if len(self._greedy(text, middle)) == len(lines):
                high = middle
            else:
                low = middle + 1
        return self._greedy(text, high) if len(lines) > 1 else lines

    def _greedy(self, text: str, max_width: int) -> list[str]:
        lines, current = [], ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            if current and self.width(trial) > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        return lines + ([current] if current else [])

    def width(self, line: str) -> int:
        return sum(int(self._font_of(part).getlength(part)) for part in self._parts(line))

    def render(self, text: str, max_width: int, align: str = "center") -> Image.Image:
        lines = self.wrap(text, max_width)
        line_h = int(self._size * 1.25)
        pad = int(self._size * 0.3)
        width = max((self.width(l) for l in lines), default=1) + 2 * pad
        image = Image.new("RGBA", (width, line_h * len(lines) + 2 * pad), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for row, line in enumerate(lines):
            x = pad if align == "left" else (width - self.width(line)) // 2
            y = pad + row * line_h
            for part in self._parts(line):
                face = self._font_of(part)
                if face is self._emoji_font:
                    draw.text((x, y + int(self._size * 0.12)), part, font=face, embedded_color=True)
                else:
                    draw.text((x, y), part, font=face, fill=self._color)
                x += int(face.getlength(part))
        if not self._shadow:
            return image
        shade = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shade.putalpha(image.getchannel("A").filter(ImageFilter.GaussianBlur(self._size / 10)).point(lambda a: a * 0.8))
        return Image.alpha_composite(shade, image)

    def _parts(self, line: str) -> list[str]:
        return [p for p in EMOJI.split(line) if p]

    def _font_of(self, part: str) -> ImageFont.FreeTypeFont:
        return self._emoji_font if EMOJI.fullmatch(part) else self._text_font


def rounded_box(size: tuple[int, int], radius: int, fill) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=fill)
    return image


def to_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGBA"), dtype=np.uint8)
