from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from bisect import bisect_right
from dataclasses import asdict, dataclass
from pathlib import Path

from fshorts.config import CommentaryConfig
from fshorts.events.candidate import Candidate, EventSource
from fshorts.gpu import register_cuda12_dlls
from fshorts.ingest import SAMPLE_RATE

# Keyword hits closer than this belong to the same commentator reaction
HIT_GROUP_SECONDS = 10.0


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, audio: Path) -> list[Word]:
        ...


class WhisperTranscriber(Transcriber):
    """faster-whisper on the GPU with word timestamps."""

    def __init__(self, config: CommentaryConfig) -> None:
        self._config = config

    def transcribe(self, audio: Path) -> list[Word]:
        import librosa

        register_cuda12_dlls()
        from faster_whisper import WhisperModel

        model = WhisperModel(self._config.model, device="cuda", compute_type=self._config.compute_type)
        # Decoded here because faster-whisper's own PyAV decoder breaks on newer av releases
        samples, _ = librosa.load(audio, sr=SAMPLE_RATE, mono=True)
        segments, _ = model.transcribe(
            samples,
            language=self._config.language,
            word_timestamps=True,
            vad_filter=True,
        )
        return [
            Word(start=round(w.start, 2), end=round(w.end, 2), text=w.word.strip())
            for segment in segments
            for w in segment.words or ()
        ]


class CachedTranscriber(Transcriber):
    """Transcription of a full match takes minutes, so it is stored next to the audio."""

    def __init__(self, inner: Transcriber, cache: Path) -> None:
        self._inner = inner
        self._cache = cache

    def transcribe(self, audio: Path) -> list[Word]:
        if self._cache.is_file():
            return [Word(**w) for w in json.loads(self._cache.read_text(encoding="utf-8"))]
        words = self._inner.transcribe(audio)
        self._cache.write_text(
            json.dumps([asdict(w) for w in words], ensure_ascii=False), encoding="utf-8"
        )
        return words


@dataclass(frozen=True)
class PhraseHit:
    time: float
    phrase: str
    weight: float


class PhraseMatcher:
    """Regex phrases searched across the running transcript, so multi-word cues like "what a shot" match."""

    def __init__(self, phrases: dict[str, float]) -> None:
        self._patterns = [(re.compile(pattern), weight) for pattern, weight in phrases.items()]

    def find(self, words: list[Word]) -> list[PhraseHit]:
        text, starts = self._join(words)
        hits = []
        for pattern, weight in self._patterns:
            for match in pattern.finditer(text):
                index = bisect_right(starts, match.start()) - 1
                hits.append(PhraseHit(words[index].start, match.group(0).strip(), weight))
        return sorted(hits, key=lambda h: h.time)

    @staticmethod
    def _join(words: list[Word]) -> tuple[str, list[int]]:
        parts, starts, offset = [], [], 0
        for word in words:
            starts.append(offset)
            token = word.text.lower() + " "
            parts.append(token)
            offset += len(token)
        return "".join(parts), starts


class CommentaryKeywordSource(EventSource):
    """Commentator cues like "goal", "what a shot" or "1-0", grouped into one candidate per reaction."""

    name = "commentary"

    def __init__(self, transcriber: Transcriber, matcher: PhraseMatcher) -> None:
        self._transcriber = transcriber
        self._matcher = matcher

    def detect(self, audio: Path) -> list[Candidate]:
        return self.detect_words(self._transcriber.transcribe(audio))

    def detect_words(self, words: list[Word]) -> list[Candidate]:
        groups: list[list[PhraseHit]] = []
        for hit in self._matcher.find(words):
            if groups and hit.time - groups[-1][-1].time <= HIT_GROUP_SECONDS:
                groups[-1].append(hit)
            else:
                groups.append([hit])
        return [self._to_candidate(group) for group in groups]

    def _to_candidate(self, group: list[PhraseHit]) -> Candidate:
        return Candidate(
            time=group[0].time,
            score=round(sum(h.weight for h in group), 3),
            sources=(self.name,),
            details=tuple(dict.fromkeys(h.phrase for h in group)),
        )
