from __future__ import annotations

import difflib
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np

# Boxes on one frame whose centres are this close (in box heights) form one line of text
SAME_LINE_HEIGHTS = 0.6
# A line seen again within this gap and near the same place continues the same track
MAX_GAP_SECONDS = 0.6
MAX_SHIFT = 0.04          # of the frame size
MIN_TEXT_RATIO = 0.6      # difflib ratio between two OCR readings of one caption
# Edited-in text stays put; ads and shirts move with the camera
MAX_OVERLAY_JITTER = 0.012
MIN_OVERLAY_SECONDS = 0.7
# Thin white glyphs fill ~15% of their box; stadium boards are almost never white
MIN_CAPTION_WHITE = 0.08
# OCR misses a caption for a few frames now and then; pieces this close are one caption
REJOIN_GAP_SECONDS = 1.5
# A logo is on screen for nearly the whole Short, in a corner band
LOGO_SHARE = 0.8
EDGE_BAND = 0.12


@dataclass(frozen=True)
class TextBox:
    """One OCR result in frame-relative coordinates (0..1)."""

    time: float
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    confidence: float
    brightness: float = 1.0   # share of near-white pixels inside the box
    emoji: bool = False       # a colourful glyph right after the text

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class TextTrack:
    """One caption line followed over time."""

    boxes: list[TextBox]

    @property
    def start(self) -> float:
        return self.boxes[0].time

    @property
    def end(self) -> float:
        return self.boxes[-1].time

    @property
    def text(self) -> str:
        # The reading OCR agreed on most often, ties broken by confidence
        counts = Counter(b.text for b in self.boxes)
        return max(self.boxes, key=lambda b: (counts[b.text], b.confidence)).text

    def median(self, field: str) -> float:
        return float(np.median([getattr(b, field) for b in self.boxes]))

    @property
    def jitter(self) -> float:
        return float(max(np.std([b.cx for b in self.boxes]), np.std([b.cy for b in self.boxes])))

    @property
    def emoji(self) -> bool:
        return sum(b.emoji for b in self.boxes) * 2 >= len(self.boxes)

    def accepts(self, box: TextBox) -> bool:
        last = self.boxes[-1]
        return (
            0 < box.time - last.time <= MAX_GAP_SECONDS
            and abs(box.cx - last.cx) <= MAX_SHIFT
            and abs(box.cy - last.cy) <= MAX_SHIFT
            and _similar(box.text, last.text)
        )


@dataclass(frozen=True)
class OverlayText:
    """An edited-in caption of a reference Short, measured for our own style."""

    text: str
    start: float
    end: float
    y: float          # vertical centre, share of frame height
    x: float
    height: float     # line height, share of frame height
    emoji: bool
    role: str         # caption, logo or scorebug

    def to_dict(self) -> dict:
        return asdict(self)


def join_lines(boxes: list[TextBox]) -> list[TextBox]:
    """Merges the word boxes of one frame into left-to-right lines."""
    lines: list[list[TextBox]] = []
    for box in sorted(boxes, key=lambda b: (b.cy, b.x0)):
        for line in lines:
            ref = line[0]
            if abs(box.cy - ref.cy) <= SAME_LINE_HEIGHTS * max(ref.height, box.height):
                line.append(box)
                break
        else:
            lines.append([box])
    merged = []
    for line in lines:
        line.sort(key=lambda b: b.x0)
        merged.append(TextBox(
            line[0].time, min(b.x0 for b in line), min(b.y0 for b in line), max(b.x1 for b in line),
            max(b.y1 for b in line), " ".join(b.text for b in line), min(b.confidence for b in line),
            float(np.mean([b.brightness for b in line])), line[-1].emoji,
        ))
    return merged


def track(frames: Iterable[list[TextBox]]) -> list[TextTrack]:
    """Links per-frame lines into tracks; a line joins the open track it continues."""
    done: list[TextTrack] = []
    open_tracks: list[TextTrack] = []
    for lines in frames:
        for line in lines:
            match = next((t for t in open_tracks if t.accepts(line)), None)
            if match is None:
                open_tracks.append(TextTrack([line]))
            else:
                match.boxes.append(line)
        if lines:
            now = lines[0].time
            done += [t for t in open_tracks if now - t.end > MAX_GAP_SECONDS]
            open_tracks = [t for t in open_tracks if now - t.end <= MAX_GAP_SECONDS]
    return _rejoin(sorted(done + open_tracks, key=lambda t: t.start))


def _rejoin(tracks: list[TextTrack]) -> list[TextTrack]:
    joined: list[TextTrack] = []
    for t in tracks:
        first = t.boxes[0]
        previous = next((p for p in reversed(joined) if 0 < first.time - p.end <= REJOIN_GAP_SECONDS
                         and abs(first.cx - p.boxes[-1].cx) <= MAX_SHIFT and abs(first.cy - p.boxes[-1].cy) <= MAX_SHIFT
                         and _similar(first.text, p.text)), None)
        if previous is None:
            joined.append(t)
        else:
            previous.boxes.extend(t.boxes)
    return joined


def _similar(a: str, b: str) -> bool:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= MIN_TEXT_RATIO


SCORE_LIKE = re.compile(r"\d+\s*[-:]\s*\d+")


def overlays(tracks: list[TextTrack], duration: float, step: float) -> list[OverlayText]:
    """Keeps the tracks that are edited-in graphics and names what each one is."""
    found = []
    for t in tracks:
        seconds = t.end - t.start + step
        if seconds < MIN_OVERLAY_SECONDS or t.jitter > MAX_OVERLAY_JITTER:
            continue
        y = t.median("cy")
        edge = y < EDGE_BAND or y > 1 - EDGE_BAND
        if edge and SCORE_LIKE.search(t.text):
            role = "scorebug"
        elif edge and seconds >= LOGO_SHARE * duration:
            role = "logo"
        elif t.median("brightness") < MIN_CAPTION_WHITE:
            continue   # dark or colourful static text: a board in the stadium, not a caption
        else:
            role = "caption"
        found.append(OverlayText(t.text, round(t.start, 2), round(t.end + step, 2), round(y, 3),
                                 round(t.median("cx"), 3), round(t.median("height"), 4), t.emoji, role))
    return found


def brightness(patch: np.ndarray) -> float:
    """Share of near-white pixels: captions are white, stadium boards rarely are."""
    if patch.size == 0:
        return 0.0
    rgb = patch.reshape(-1, 3).astype(np.int16)
    white = (rgb.min(axis=1) > 200) & (rgb.max(axis=1) - rgb.min(axis=1) < 40)
    return float(white.mean())


def has_emoji(patch: np.ndarray) -> bool:
    """Emoji are saturated and mostly not pitch green."""
    if patch.size == 0:
        return False
    rgb = patch.reshape(-1, 3).astype(np.float32) / 255
    high, low = rgb.max(axis=1), rgb.min(axis=1)
    saturated = (high > 0.55) & ((high - low) / np.maximum(high, 1e-6) > 0.55)
    green = (rgb[:, 1] >= rgb[:, 0]) & (rgb[:, 1] >= rgb[:, 2])
    return float((saturated & ~green).mean()) > 0.12
