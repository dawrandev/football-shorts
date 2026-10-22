from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.signal import find_peaks

from fshorts.config import AudioPeaksConfig
from fshorts.events.candidate import Candidate, EventSource
from fshorts.ingest import SAMPLE_RATE

FLUX_WEIGHT = 0.3


class AudioExcitementSource(EventSource):
    """Finds crowd roars and commentator outbursts: loudness well above the local baseline."""

    name = "audio"

    def __init__(self, config: AudioPeaksConfig) -> None:
        self._config = config

    def detect(self, audio: Path) -> list[Candidate]:
        samples, _ = librosa.load(audio, sr=SAMPLE_RATE, mono=True)
        return self.detect_samples(samples)

    def detect_samples(self, samples: np.ndarray) -> list[Candidate]:
        hop = self._config.hop_seconds
        frames = round(hop * SAMPLE_RATE)
        loudness = librosa.amplitude_to_db(
            librosa.feature.rms(y=samples, frame_length=2 * frames, hop_length=frames)[0], ref=1.0
        )
        flux = librosa.onset.onset_strength(y=samples, sr=SAMPLE_RATE, hop_length=frames)
        length = min(len(loudness), len(flux))
        db_rise = self._detrended(loudness[:length])
        score = (self._zscore(db_rise) + FLUX_WEIGHT * self._zscore(self._detrended(flux[:length]))) / (
            1 + FLUX_WEIGHT
        )

        peaks, _ = find_peaks(score, height=self._config.min_zscore, distance=max(1, round(self._config.min_gap_seconds / hop)))
        # z-scores are relative, so plain noise always has some; the dB rise is the absolute check
        loud_peaks = [i for i in peaks if db_rise[i] >= self._config.min_db_rise]
        return [
            Candidate(time=round(float(i * hop), 2), score=round(float(score[i]), 3), sources=(self.name,))
            for i in loud_peaks
        ]

    def _detrended(self, values: np.ndarray) -> np.ndarray:
        """Values minus a rolling median baseline, then smoothed."""
        hop = self._config.hop_seconds
        baseline = median_filter(values, size=max(1, round(self._config.baseline_seconds / hop)), mode="nearest")
        return uniform_filter1d(values - baseline, size=max(1, round(self._config.smooth_seconds / hop)))

    @staticmethod
    def _zscore(values: np.ndarray) -> np.ndarray:
        spread = values.std()
        return values / spread if spread > 0 else np.zeros_like(values)
