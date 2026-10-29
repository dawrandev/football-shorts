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
# One replay angle appended to a Short: long enough to see the action again, short enough to keep pace
REPLAY_MIN_SECONDS = 2.5
REPLAY_MAX_SECONDS = 7.0
# Camera views a replay angle is judged by; the angle from behind the goal shows a finish best
REPLAY_VIEWS = {"goalmouth": 2.0, "wide": 1.0}
# Dropped at both ends of an angle: the dissolve into and out of it
REPLAY_EDGE_SECONDS = 0.25


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
        # The logo wipe that opens a replay is not part of the live clip
        wipe = self._timeline.first_break(moment + 1.0, post)
        end = min(moment + post, ceiling, wipe if wipe is not None else float("inf"))
        return ClipPlan(clip["kind"], moment, start, end, clip["score"], clip["label"], floor=floor, ceiling=ceiling)

    def _replay_end_before(self, moment: float) -> float:
        stretches = self._timeline.hidden_stretches(2.0)
        return max((end for _, end in stretches if end <= moment - 3.0), default=0.0)

    def _replay_start_after(self, moment: float) -> float:
        return min((start for start, _ in self._timeline.hidden_stretches(2.0) if start > moment + 0.5),
                   default=float("inf"))


class ReplayAnglePicker:
    """Picks the one replay angle (a single camera shot inside the broadcast replay) a Short ends with.

    Viewers asked to see goals again; the director's replay already has the best angles, so we take
    the shot that shows the play best: mostly goal-mouth or wide views, at least a few seconds long.
    """

    def __init__(self, timeline: BroadcastTimeline) -> None:
        self._timeline = timeline

    def pick(self, start: float, end: float, cuts: list[float]) -> tuple[float, float] | None:
        # Replays cut between angles with dissolves the scene detector often misses, so the angle is
        # a run of play views inside a cut-bounded shot, trimmed off the transition at both ends
        bounds = [start] + [c for c in sorted(cuts) if start < c < end] + [end]
        best, best_score = None, 0.0
        for shot_start, shot_end in zip(bounds, bounds[1:]):
            for a, b in self._timeline.runs(shot_start, shot_end, tuple(REPLAY_VIEWS)):
                a, b = a + REPLAY_EDGE_SECONDS, b - REPLAY_EDGE_SECONDS
                if b - a < REPLAY_MIN_SECONDS:
                    continue
                views = self._timeline.views_between(a, b)
                weight = sum(REPLAY_VIEWS.get(v, 0.0) for v in views) / max(len(views), 1)
                score = weight * min(b - a, REPLAY_MAX_SECONDS)
                if score > best_score:
                    best, best_score = (a, min(b, a + REPLAY_MAX_SECONDS)), score
        return best
