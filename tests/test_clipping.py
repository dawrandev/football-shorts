import json

import pytest

from fshorts.clipping import ClipPlan, ClipPlanner, SceneCutDetector, SceneSnapper
from fshorts.config import ClipConfig
from fshorts.events import Candidate
from fshorts.review import LabelStore, ReviewSession
from fshorts.scoreboard import ScoreChange, ScoreReading

CONFIG = ClipConfig(
    pre_seconds=12, post_seconds=6, goal_pre_seconds=20, goal_post_seconds=8,
    include_replay=True, replay_max_seconds=25, max_chances=2, snap_seconds=4,
)


def readings(times, score):
    return [ScoreReading(float(t), "POR", "ESP", score[0], score[1], None) for t in times]


def test_goal_clip_keeps_build_up_and_replay():
    # Old score until 100, bug hidden 104..130 (celebration and replay), new score after
    series = readings(range(0, 101), (0, 0)) + readings(range(101, 104), (1, 0)) + readings(range(130, 200), (1, 0))
    goal = ScoreChange(101.0, (0, 0), (1, 0))

    [plan] = ClipPlanner(CONFIG).plan([goal], series, [], duration=6000)

    assert plan.kind == "goal" and plan.label == "1-0"
    assert plan.anchor == 101.0
    assert plan.start == 81.0
    assert plan.end == 130.0


def test_goal_with_long_hidden_bug_uses_commentary_cue():
    series = readings(range(0, 3651), (2, 2)) + readings(range(3760, 3800), (2, 3))
    goal = ScoreChange(3760.0, (2, 2), (2, 3))
    cue = Candidate(3702.0, 3.0, ("commentary",), ("what a shot",))

    [goal_plan, *_] = ClipPlanner(CONFIG).plan([goal], series, [cue], duration=6000)

    assert goal_plan.anchor == 3702.0


def test_chances_skip_goal_windows_and_respect_limit():
    series = readings(range(0, 101), (0, 0)) + readings(range(101, 3100), (1, 0))
    goal = ScoreChange(101.0, (0, 0), (1, 0))
    candidates = [
        Candidate(100.0, 9.0, ("commentary",), ("goal",)),   # inside the goal clip
        Candidate(1000.0, 5.0, ("audio",)),
        Candidate(2000.0, 4.0, ("commentary",), ("save",)),
        Candidate(3000.0, 1.0, ("audio",)),
    ]

    plans = ClipPlanner(CONFIG).plan([goal], series, candidates, duration=6000)

    assert [(p.kind, p.anchor) for p in plans] == [("goal", 101.0), ("chance", 1000.0), ("chance", 2000.0)]
    assert plans[1].start == 988.0 and plans[1].end == 1006.0


def test_chances_outside_match_play_are_dropped():
    series = readings(range(150, 5900), (0, 0))
    candidates = [Candidate(20.0, 9.0, ("commentary",)), Candidate(3000.0, 1.0, ("audio",)),
                  Candidate(5950.0, 9.0, ("commentary",))]

    plans = ClipPlanner(CONFIG).plan([], series, candidates, duration=6000)

    assert [p.anchor for p in plans] == [3000.0]


def test_plans_are_clamped_to_video():
    plans = ClipPlanner(CONFIG).plan([], [], [Candidate(5.0, 1.0, ("audio",))], duration=8.0)

    assert (plans[0].start, plans[0].end) == (0.0, 8.0)


class FakeCuts(SceneCutDetector):
    def __init__(self, cuts):
        self._cuts = cuts

    def cuts(self, video, start, end):
        return [c for c in self._cuts if start <= c <= end]


def test_snapper_widens_to_nearby_cuts_only():
    plan = ClipPlan("chance", 100.0, 88.0, 106.0, 1.0, "x")

    snapped = SceneSnapper(FakeCuts([85.5, 90.0, 108.0, 120.0]), snap_seconds=4).snap(None, plan)

    # 90 is inside the clip (start may only move earlier), 120 is too far
    assert (snapped.start, snapped.end) == (85.5, 108.0)


def test_snapper_respects_floor_and_ceiling():
    plan = ClipPlan("chance", 100.0, 88.0, 106.0, 1.0, "x", floor=87.0, ceiling=107.0)

    snapped = SceneSnapper(FakeCuts([85.5, 108.0]), snap_seconds=4).snap(None, plan)

    assert (snapped.start, snapped.end) == (88.0, 106.0)


def test_snapper_without_cuts_keeps_plan():
    plan = ClipPlan("chance", 100.0, 88.0, 106.0, 1.0, "x")

    assert SceneSnapper(FakeCuts([]), snap_seconds=4).snap(None, plan) == plan


CLIPS = [
    {"id": "01_goal_101", "file": "01_goal_101.mp4", "kind": "goal", "label": "1-0", "start": 81.0, "end": 130.0},
    {"id": "02_chance_1000", "file": "02_chance_1000.mp4", "kind": "chance", "label": "save",
     "start": 988.0, "end": 1006.0},
]


def test_review_saves_labels_and_skips_done_clips(tmp_path):
    store = LabelStore(tmp_path / "labels" / "m.json")
    answers = iter(["y", "g", "n", "b"])
    shown = []

    reviewed = ReviewSession(store, ask=lambda _: next(answers), show=shown.append).run(CLIPS, tmp_path)

    labels = store.load()
    assert reviewed == 2 and len(shown) == 2
    assert labels["01_goal_101"].accepted and labels["01_goal_101"].reason == "goal"
    assert not labels["02_chance_1000"].accepted and labels["02_chance_1000"].reason == "boring"

    # A second run has nothing left to ask
    assert ReviewSession(store, ask=lambda _: pytest.fail("asked again"), show=shown.append).run(CLIPS, tmp_path) == 0


def test_review_quit_keeps_earlier_labels(tmp_path):
    store = LabelStore(tmp_path / "m.json")
    answers = iter(["n", "x", "q"])

    ReviewSession(store, ask=lambda _: next(answers), show=lambda _: None).run(CLIPS, tmp_path)

    saved = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert [(l["clip_id"], l["reason"]) for l in saved] == [("01_goal_101", "bad_cut")]
