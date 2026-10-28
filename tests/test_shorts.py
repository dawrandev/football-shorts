import numpy as np
import pytest

from fshorts.broadcast import BroadcastTimeline
from fshorts.clipping.shorts import GoalMomentRefiner, ShortsPlanner
from fshorts.config import ShortTiming

RATE = 1000


def crowd(seconds, roar_at):
    """Quiet noise with a crowd roar that peaks at `roar_at`."""
    t = np.arange(int(seconds * RATE)) / RATE
    loudness = 0.02 + 0.5 * np.exp(-((t - roar_at) / 1.5) ** 2)
    return np.random.default_rng(0).normal(0, 1, len(t)) * loudness


def test_goal_moment_is_just_before_the_roar_peak():
    refiner = GoalMomentRefiner(crowd(200, roar_at=95.0), RATE)

    # the score bug updated at 100 s, five seconds after the roar
    assert refiner.refine(100.0) == pytest.approx(93.5, abs=0.3)


def timeline(spans, seconds=300):
    bug, views = [True] * seconds, ["wide"] * seconds
    for start, end in spans:
        bug[start:end] = [False] * (end - start)
    return BroadcastTimeline(1.0, tuple(bug), tuple(views))


class FixedMoment:
    def refine(self, anchor):
        return anchor - 5


def test_goal_short_is_timed_around_the_real_moment():
    planner = ShortsPlanner(ShortTiming(), timeline([(120, 150)]), FixedMoment())

    plan = planner.plan({"kind": "goal", "anchor": 105.0, "score": 1000, "label": "1-0"})

    assert (plan.anchor, plan.start, plan.end) == (100.0, 88.0, 104.0)


def test_chance_short_stops_before_its_replay_and_skips_earlier_replay_tail():
    planner = ShortsPlanner(ShortTiming(), timeline([(80, 93), (101, 113)]), FixedMoment())

    plan = planner.plan({"kind": "chance", "anchor": 100.0, "score": 4, "label": "shot_saved: Son"})

    assert plan.start == 93.0 and plan.end == 101.0 and plan.ceiling == 101.0


def test_replays_get_no_short():
    planner = ShortsPlanner(ShortTiming(), timeline([]), FixedMoment())
    assert planner.plan({"kind": "goal_replay", "anchor": 1.0, "score": 1, "label": ""}) is None
