from pathlib import Path

import numpy as np
import pytest

from fshorts.config import AppConfig, AudioPeaksConfig
from fshorts.events import (
    AudioExcitementSource,
    Candidate,
    CandidateMerger,
    CommentaryKeywordSource,
    PhraseMatcher,
    Transcriber,
    Word,
)
from fshorts.ingest import SAMPLE_RATE

AUDIO_CONFIG = AudioPeaksConfig(
    hop_seconds=0.5, baseline_seconds=60, smooth_seconds=2, min_gap_seconds=20, min_zscore=2.0,
    min_db_rise=3.0,
)
PHRASES = {
    r"\bgo+a+l+\b": 3.0,
    r"\bгол+\b": 3.0,
    r"\bpenalt(y|ies)\b": 1.5,
    r"\b\d\s*-\s*\d\b": 2.0,
    r"\bwhat an? (goal|shot)\b": 3.0,
}


def crowd_noise(seconds: float, roars: list[tuple[float, float]]) -> np.ndarray:
    """Quiet noise with loud bursts at (start, length) positions."""
    rng = np.random.default_rng(0)
    samples = rng.normal(0, 0.02, int(seconds * SAMPLE_RATE)).astype(np.float32)
    for start, length in roars:
        a, b = int(start * SAMPLE_RATE), int((start + length) * SAMPLE_RATE)
        samples[a:b] *= 12
    return samples


def test_audio_peaks_find_roars():
    samples = crowd_noise(300, roars=[(60, 6), (200, 6)])

    found = AudioExcitementSource(AUDIO_CONFIG).detect_samples(samples)

    assert len(found) == 2
    assert found[0].time == pytest.approx(63, abs=5)
    assert found[1].time == pytest.approx(203, abs=5)
    assert all(c.sources == ("audio",) for c in found)


def test_audio_peaks_ignore_flat_audio():
    assert AudioExcitementSource(AUDIO_CONFIG).detect_samples(crowd_noise(300, roars=[])) == []


def words_from(text: str, start: float = 0.0, step: float = 0.5) -> list[Word]:
    return [Word(start + i * step, start + i * step + 0.4, t) for i, t in enumerate(text.split())]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Goooal! What a moment", ["goooal"]),
        ("It's 1 -0 Portugal", ["1 -0"]),
        ("Oh, what a shot that is!", ["what a shot"]),
        ("Гол! Красиво", ["гол"]),
        ("the goalkeeper passes it short", []),
    ],
)
def test_phrase_matcher(text, expected):
    hits = PhraseMatcher(PHRASES).find(words_from(text))
    assert [h.phrase for h in hits] == expected


@pytest.mark.parametrize(
    "text, matched",
    [("it's 1 -0 Portugal", True), ("now 2-1 to France", True), ("they line up 4-4-2", False),
     ("a 4-3-3 shape", False)],
)
def test_repo_score_phrase_skips_formations(text, matched):
    phrases = AppConfig.load(Path(__file__).resolve().parents[1] / "config.yaml").events.commentary.phrases
    hits = [h for h in PhraseMatcher(phrases).find(words_from(text)) if any(ch.isdigit() for ch in h.phrase)]
    assert bool(hits) == matched


def test_phrase_hit_takes_time_of_first_word():
    words = words_from("long ball forward and what a shot", start=100.0)

    hits = PhraseMatcher(PHRASES).find(words)

    assert hits[0].time == words[4].start


class FakeTranscriber(Transcriber):
    def __init__(self, words):
        self._words = words

    def transcribe(self, audio):
        return self._words


def test_commentary_groups_nearby_hits():
    words = words_from("Goal! Goooal! it is", start=100.0) + words_from("a penalty now", start=500.0)
    source = CommentaryKeywordSource(FakeTranscriber(words), PhraseMatcher(PHRASES))

    found = source.detect(audio=None)

    assert [c.time for c in found] == [100.0, 500.5]
    assert found[0].score == 6.0
    assert found[1].details == ("penalty",)


def test_merger_rewards_agreeing_sources():
    candidates = [
        Candidate(100.0, 3.0, ("audio",)),
        Candidate(108.0, 3.0, ("commentary",), ("goal!",)),
        Candidate(400.0, 4.0, ("audio",)),
    ]

    merged = CandidateMerger(merge_seconds=15, max_candidates=10).merge(candidates)

    assert [c.time for c in merged] == [100.0, 400.0]
    assert merged[0].sources == ("audio", "commentary")
    assert merged[0].score == 12.0


def test_merger_keeps_strongest_in_time_order():
    candidates = [Candidate(t, s, ("audio",)) for t, s in [(10, 1.0), (100, 5.0), (200, 3.0), (300, 4.0)]]

    merged = CandidateMerger(merge_seconds=15, max_candidates=2).merge(candidates)

    assert [c.time for c in merged] == [100, 300]


def test_merger_window_does_not_chain():
    candidates = [Candidate(t, 1.0, ("commentary",)) for t in (100.0, 110.0, 120.0, 130.0)]

    merged = CandidateMerger(merge_seconds=25, max_candidates=10).merge(candidates)

    assert [c.time for c in merged] == [100.0, 130.0]
