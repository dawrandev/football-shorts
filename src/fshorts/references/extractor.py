from __future__ import annotations

from pathlib import Path

import numpy as np

from fshorts.ingest import FfprobeProber, FrameSampler, Region
from fshorts.references.texts import OverlayText, TextBox, brightness, has_emoji, join_lines, overlays, track

# Reference Shorts are up to 1080x1920; OCR at this width still reads 2%-high captions
OCR_WIDTH = 720


class ReferenceTextExtractor:
    """Finds the edited-in captions of a reference Short with their place, size and timing."""

    def __init__(self, sampler: FrameSampler, prober: FfprobeProber, fps: float = 4.0, gpu: bool = True,
                 min_confidence: float = 0.4) -> None:
        import easyocr

        self._reader = easyocr.Reader(["en"], gpu=gpu, verbose=False)
        self._sampler = sampler
        self._prober = prober
        self._fps = fps
        self._min_confidence = min_confidence

    def extract(self, video: Path) -> tuple[float, list[OverlayText]]:
        info = self._prober.probe(video)
        width = OCR_WIDTH
        height = round(info.height * OCR_WIDTH / info.width / 2) * 2
        frames = (
            self._lines(time, frame)
            for time, frame in self._sampler.sample(video, self._fps, Region(0, 0, info.width, info.height),
                                                    size=(width, height))
        )
        return info.duration_seconds, overlays(track(frames), info.duration_seconds, 1 / self._fps)

    def _lines(self, time: float, frame: np.ndarray) -> list[TextBox]:
        h, w = frame.shape[:2]
        boxes = []
        for box, text, confidence in self._reader.readtext(frame):
            if confidence < self._min_confidence or not text.strip():
                continue
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            x0, x1, y0, y1 = int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))
            tail = frame[y0:y1, x1:min(w, x1 + int(1.6 * (y1 - y0)))]
            boxes.append(TextBox(
                round(time, 2), x0 / w, y0 / h, x1 / w, y1 / h, text.strip(), float(confidence),
                brightness(frame[y0:y1, x0:x1]), has_emoji(tail),
            ))
        return join_lines(boxes)


def pitch_share(sampler: FrameSampler, prober: FfprobeProber, video: Path, fps: float = 1.0) -> float:
    """Median share of grass-green pixels per frame: in-game Shorts sit well above 0.3, interviews near 0."""
    info = prober.probe(video)
    shares = []
    for _, frame in sampler.sample(video, fps, Region(0, 0, info.width, info.height), size=(90, 160)):
        rgb = frame.reshape(-1, 3).astype(np.int16)
        r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
        shares.append(float(((g > r + 15) & (g > b + 15) & (g > 60)).mean()))
    return float(np.median(shares)) if shares else 0.0
