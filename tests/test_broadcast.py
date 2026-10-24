import json

import numpy as np

from fshorts.broadcast import BroadcastTimeline, RecapDetector, Replay, ScoreBugDetector
from fshorts.clipping import ClipPlanner
from fshorts.config import ClipConfig
from fshorts.events import Word
from fshorts.events.replay_events import ReplayEvent, ReplayEventClassifier, TextGenerator
from fshorts.scoreboard import ScoreChange

CONFIG = ClipConfig(
    pre_seconds=12, post_seconds=6, goal_pre_seconds=20, goal_post_seconds=8,
    include_replay=True, replay_max_seconds=25, max_chances=5, snap_seconds=4,
)


def timeline(spans, seconds=600):
    """1 fps timeline built from (start, end, view, bug_visible) spans; the rest is a live wide shot."""
    bug, views = [True] * seconds, ["wide"] * seconds
    for start, end, view, visible in spans:
        for t in range(start, end):
            bug[t], views[t] = visible, view
    return BroadcastTimeline(1.0, tuple(bug), tuple(views))


def test_bug_detector_learns_template_from_ocr_frames():
    rng = np.random.default_rng(0)
    background = rng.integers(0, 255, (100, 20, 40)).astype(np.uint8)   # changing pitch and crowd
    crops = background.copy()
    crops[:60, 5:10, 5:30] = 200                                       # bug on screen in the first 60
    known = np.zeros(100, dtype=bool)
    known[:40:2] = True                                                # OCR read only some of them

    detector = ScoreBugDetector(stable_fraction=0.1)
    detector.fit(crops, known)

    visible = detector.visible(crops)
    assert visible[:60].all() and not visible[60:].any()


def test_replay_event_is_last_live_wide_frame_before_it():
    # live wide until 100, close-ups 100..106 (bug on), replay 106..118 (bug off), live again
    tl = timeline([(100, 106, "close", True), (106, 118, "close", False)])

    [replay] = tl.replays()

    assert (replay.start, replay.end) == (106.0, 118.0)
    assert replay.event == 99.0


def test_long_hidden_stretch_is_not_a_replay():
    tl = timeline([(100, 300, "crowd", False)])
    assert tl.replays() == []


def test_recap_detector_matches_reaired_footage():
    rng = np.random.default_rng(1)
    thumbs = rng.normal(size=(400, 64))
    thumbs[300:320] = thumbs[50:70]                                    # replay at 300 re-airs 50..70
    thumbs /= np.linalg.norm(thumbs, axis=1, keepdims=True)
    detector = RecapDetector(sampler=None, fps=1.0)

    assert detector.recaps(thumbs, [Replay(300, 320, 290), Replay(350, 365, 340)]) == [True, False]


class FakeGenerator(TextGenerator):
    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.answer


def test_replay_classifier_marks_replay_lines_and_parses_json():
    words = [Word(95.0, 95.4, "Son"), Word(96.0, 96.4, "shoots!"), Word(108.0, 108.4, "Great"),
             Word(108.5, 108.9, "save.")]
    generator = FakeGenerator('Sure: {"kind": "shot_saved", "player": "Son", "summary": "Son shot saved"}')

    [event] = ReplayEventClassifier(generator).classify([Replay(106, 118, 99)], words)

    assert (event.kind, event.player) == ("shot_saved", "Son")
    assert "[-4s] Son shoots!" in generator.prompts[0]
    assert "[+9s] [replay] Great save." in generator.prompts[0]


def test_replay_classifier_falls_back_on_bad_answer():
    [event] = ReplayEventClassifier(FakeGenerator("no idea")).classify([Replay(10, 20, 5)], [])
    assert event.kind == "other" and event.player is None


def event(start, end, live, kind, player="Son", recap=False):
    return ReplayEvent(Replay(start, end, live), kind, player, "", recap)


def test_chance_clip_is_live_build_up_and_replay_is_separate():
    tl = timeline([(100, 106, "close", True), (106, 118, "close", False)])

    plans = ClipPlanner(CONFIG).plan([], [], [], 600, tl, [event(106, 118, 99, "shot_saved")])

    assert [(p.kind, p.start, p.end) for p in plans] == [("chance", 87.0, 103.0), ("chance_replay", 106.0, 118.0)]
    assert plans[0].ceiling == 106.0 and plans[0].label == "shot_saved: Son"


def test_chance_start_skips_bench_and_earlier_replay():
    # an earlier replay ends at 85 and a bench shot follows until 90: the clip opens at 90
    tl = timeline([(70, 85, "close", False), (85, 90, "crowd", True), (100, 106, "close", True),
                   (106, 118, "close", False)])

    [chance, _] = ClipPlanner(CONFIG).plan([], [], [], 600, tl, [event(106, 118, 99, "near_miss")])

    assert chance.start == 90.0 and chance.floor == 85.0


def test_fouls_recaps_and_goal_replays_are_not_chances():
    tl = timeline([(300, 320, "close", False), (400, 410, "close", False), (500, 510, "close", False)])
    goal = ScoreChange(200.0, (0, 0), (1, 0))
    events = [event(300, 320, 290, "shot_off_target"),        # within the goal's replay window
              event(400, 410, 395, "foul"),
              event(500, 510, 495, "shot_saved", recap=True)]

    plans = ClipPlanner(CONFIG).plan([goal], [], [], 600, tl, events)

    assert [p.kind for p in plans] == ["goal", "goal_replay"]
    assert plans[1].start == 300.0


def test_goal_clip_never_opens_on_replay_tail():
    # replay of an older goal until 292, the next goal at 308: start moves from 288 to 292
    tl = timeline([(265, 292, "close", False)])

    [plan] = ClipPlanner(CONFIG).plan([ScoreChange(308.0, (3, 0), (4, 0))], [], [], 600, tl, [])

    assert plan.start == 292.0


def test_replay_event_round_trip():
    original = event(1, 2, None, "skill", recap=True)
    assert ReplayEvent.from_dict(json.loads(json.dumps(original.to_dict()))) == original


def test_replay_classifier_drops_pronouns_as_player():
    answer = '{"kind": "shot_saved", "player": "null", "summary": "x"}'
    [event] = ReplayEventClassifier(FakeGenerator(answer)).classify([Replay(10, 20, 5)], [])
    assert event.player is None
