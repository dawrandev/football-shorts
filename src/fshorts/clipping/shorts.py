from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d

from fshorts.broadcast import BroadcastTimeline
from fshorts.clipping.planner import ClipPlan
from fshorts.config import ShortTiming

# Loudness envelope resolution and smoothing
HOP_SECONDS = 0.1
SMOOTH_SECONDS = 1.0
# Kinds that get a Short; replays stay full-length assets
SHORT_KINDS = ("goal", "chance", "skill")


class GoalMomentRefiner:
    """Finds the moment the ball goes in, which the score bug only reports seconds later.

    The crowd roar peaks ~1.5 s after the ball crosses the line; the bug updates 0-6 s after that.
    Checked frame by frame on the BRA-KOR goals: the roar peak minus 1.5 s lands within ~1 s.
    """

    def __init__(self, samples: np.ndarray, sample_rate: int, before: float = 15.0, after: float = 3.0,
                 lead: float = 1.5) -> None:
        hop = int(sample_rate * HOP_SECONDS)
        frames = len(samples) // hop
        power = (samples[: frames * hop].astype(np.float64).reshape(frames, hop) ** 2).mean(axis=1)
        self._loudness = uniform_filter1d(10 * np.log10(power + 1e-12), int(SMOOTH_SECONDS / HOP_SECONDS))
        self._before = before
        self._after = after
        self._lead = lead

    @classmethod
    def from_wav(cls, path: Path) -> GoalMomentRefiner:
        import librosa

        samples, rate = librosa.load(path, sr=None, mono=True)
        return cls(samples, int(rate))

    def refine(self, anchor: float) -> float:
        a = max(0, int((anchor - self._before) / HOP_SECONDS))
        b = min(len(self._loudness), int((anchor + self._after) / HOP_SECONDS))
        if b <= a:
            return anchor
        peak = (a + int(np.argmax(self._loudness[a:b]))) * HOP_SECONDS
        return peak - self._lead


class ShortsPlanner:
    """Cuts each goal, chance or skill clip down to a 10-20 s Short around the moment itself."""

    def __init__(self, timing: ShortTiming, timeline: BroadcastTimeline, refiner: GoalMomentRefiner) -> None:
        self._timing = timing
        self._timeline = timeline
        self._refiner = refiner

    def plan(self, clip: dict) -> ClipPlan | None:
        if clip["kind"] not in SHORT_KINDS:
            return None
        if clip["kind"] == "goal":
            moment = self._refiner.refine(clip["anchor"])
            pre, post = self._timing.goal_pre, self._timing.goal_post
        else:
            moment = clip["anchor"]
            pre, post = self._timing.chance_pre, self._timing.chance_post
        floor = self._replay_end_before(moment)
        ceiling = self._replay_start_after(moment)
        start = max(moment - pre, floor)
        live = self._timeline.first_on_air_play(start, within=max(0.0, moment - 3.0 - start))
        start = live if live is not None else start
        end = min(moment + post, ceiling)
        return ClipPlan(clip["kind"], moment, start, end, clip["score"], clip["label"], floor=floor, ceiling=ceiling)

    def _replay_end_before(self, moment: float) -> float:
        stretches = self._timeline.hidden_stretches(2.0)
        return max((end for _, end in stretches if end <= moment - 3.0), default=0.0)

    def _replay_start_after(self, moment: float) -> float:
        return min((start for start, _ in self._timeline.hidden_stretches(2.0) if start > moment + 0.5),
                   default=float("inf"))
