from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from fshorts.ingest import FrameSampler, Region
from fshorts.scoreboard.reading import OcrToken, ScoreBugParser, ScoreReading


class OcrEngine(ABC):
    @abstractmethod
    def read(self, image: np.ndarray) -> list[OcrToken]:
        ...


class EasyOcrEngine(OcrEngine):
    def __init__(self, gpu: bool = True) -> None:
        import easyocr

        self._reader = easyocr.Reader(["en"], gpu=gpu, verbose=False)

    def read(self, image: np.ndarray) -> list[OcrToken]:
        return [
            OcrToken(
                x=(box[0][0] + box[1][0]) / 2,
                y=(box[0][1] + box[2][1]) / 2,
                text=text,
                confidence=float(confidence),
            )
            for box, text, confidence in self._reader.readtext(image)
        ]


class ScoreBugReader:
    """Samples the score-bug region once per interval and keeps every parsable reading."""

    def __init__(self, sampler: FrameSampler, ocr: OcrEngine, parser: ScoreBugParser) -> None:
        self._sampler = sampler
        self._ocr = ocr
        self._parser = parser

    def read(self, video: Path, region: Region, fps: float) -> list[ScoreReading]:
        readings = []
        for time, frame in self._sampler.sample(video, fps, region):
            reading = self._parser.parse(round(time, 2), self._ocr.read(frame))
            if reading is not None:
                readings.append(reading)
        return readings


class CachedScoreBugReader:
    """OCR over a whole match takes minutes, so readings are stored in the match workspace."""

    def __init__(self, inner: ScoreBugReader, cache: Path) -> None:
        self._inner = inner
        self._cache = cache

    def read(self, video: Path, region: Region, fps: float) -> list[ScoreReading]:
        if self._cache.is_file():
            return [ScoreReading.from_dict(r) for r in json.loads(self._cache.read_text(encoding="utf-8"))]
        readings = self._inner.read(video, region, fps)
        self._cache.write_text(json.dumps([r.to_dict() for r in readings]), encoding="utf-8")
        return readings
