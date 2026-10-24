from __future__ import annotations

import numpy as np


class ScoreBugDetector:
    """Tells per frame whether the score bug is on screen by comparing its area to a learned template.

    OCR misses the bug now and then, so it only calibrates: the template is the per-pixel median over
    frames where OCR read a score, and only pixels that stay stable across them (the graphic, not the
    pitch behind it) are compared.
    """

    def __init__(self, stable_fraction: float = 0.05, max_difference: float = 10.0) -> None:
        self._stable_fraction = stable_fraction
        self._max_difference = max_difference
        self._template: np.ndarray | None = None
        self._mask: np.ndarray | None = None

    def fit(self, crops: np.ndarray, known_visible: np.ndarray) -> None:
        reference = crops[known_visible].astype(np.float32)
        if len(reference) < 10:
            raise ValueError("Too few frames with a readable score bug to build a template")
        spread = reference.std(axis=0)
        self._template = np.median(reference, axis=0)
        self._mask = spread <= np.quantile(spread, self._stable_fraction)

    def differences(self, crops: np.ndarray) -> np.ndarray:
        if self._template is None:
            raise RuntimeError("fit() first")
        return np.abs(crops.astype(np.float32) - self._template)[:, self._mask].mean(axis=1)

    def visible(self, crops: np.ndarray) -> np.ndarray:
        return self.differences(crops) <= self._max_difference
