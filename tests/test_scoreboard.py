import json

import pytest

from fshorts.evaluation import GoalDetectionEvaluator, GroundTruth
from fshorts.scoreboard import GoalExtractor, OcrToken, ScoreBugParser, ScoreReading, ScoreTimeline


def tokens(*items):
    return [OcrToken(x, y, text, conf) for x, y, text, conf in items]


# Token positions taken from real EasyOCR output on the test matches
BUG_2018 = tokens((212, 80, "POR", 1.0), (293, 80, "1", 1.0), (351, 81, "0", 1.0),
                  (432, 80, "ESP", 1.0), (603, 81, "7.30", 0.87))
BUG_2022 = tokens((173, 80, "17:18", 0.37), (370, 79, "BRA", 1.0), (448, 78, "2", 1.0),
                  (551, 79, "0", 1.0), (628, 79, "KOR", 1.0))


def test_parses_2018_layout():
    reading = ScoreBugParser().parse(600.0, BUG_2018)

    assert (reading.home_code, reading.away_code, reading.score) == ("POR", "ESP", (1, 0))
    assert reading.clock_seconds == 450


def test_parses_2022_layout_with_clock_on_the_left():
    reading = ScoreBugParser().parse(1200.0, BUG_2022)

    assert (reading.home_code, reading.away_code, reading.score) == ("BRA", "KOR", (2, 0))
    assert reading.clock_seconds == 17 * 60 + 18


def test_glued_digits_are_split():
    glued = tokens((212, 80, "FRA", 1.0), (320, 80, "10", 0.9), (432, 80, "ARG", 1.0))

    assert ScoreBugParser().parse(0.0, glued).score == (1, 0)


@pytest.mark.parametrize(
    "items",
    [
        [],
        [(212, 80, "POR", 1.0), (432, 80, "ESP", 1.0)],
        [(212, 80, "POR", 1.0), (293, 80, "1", 1.0), (351, 81, "0", 1.0), (432, 140, "ESP", 1.0)],
        [(212, 80, "POR", 1.0), (293, 80, "1", 0.1), (351, 81, "0", 1.0), (432, 80, "ESP", 1.0)],
    ],
    ids=["empty", "no-digits", "other-row", "low-confidence"],
)
def test_unreadable_bug_gives_none(items):
    assert ScoreBugParser().parse(0.0, tokens(*items)) is None


def readings(*pairs):
    return [ScoreReading(t, "POR", "ESP", h, a, None) for t, (h, a) in pairs]


def test_timeline_confirms_change_after_consecutive_readings():
    series = readings((0, (0, 0)), (1, (0, 0)), (2, (0, 0)), (10, (1, 0)), (11, (1, 0)), (12, (1, 0)))

    changes = ScoreTimeline(confirmations=3).changes(series)

    assert [(c.time, c.before, c.after, c.kind) for c in changes] == [(10, (0, 0), (1, 0), "goal_home")]


def test_timeline_ignores_single_misread():
    series = readings((0, (1, 0)), (1, (1, 0)), (2, (1, 0)), (3, (7, 0)), (4, (1, 0)), (5, (1, 0)))

    assert ScoreTimeline(confirmations=3).changes(series) == []


def test_timeline_bridges_seconds_without_bug():
    # Readings at 20 and 45 are missing (replay); the streak still completes
    series = readings((0, (0, 0)), (1, (0, 0)), (2, (0, 0)), (19, (0, 1)), (44, (0, 1)), (60, (0, 1)))

    changes = ScoreTimeline(confirmations=3).changes(series)

    assert [(c.time, c.kind) for c in changes] == [(19, "goal_away")]


def test_var_revert_cancels_goal():
    series = readings(
        (0, (0, 0)), (1, (0, 0)), (2, (0, 0)),
        (10, (1, 0)), (11, (1, 0)), (12, (1, 0)),
        (90, (0, 0)), (91, (0, 0)), (92, (0, 0)),
        (300, (0, 1)), (301, (0, 1)), (302, (0, 1)),
    )

    goals = GoalExtractor().goals(ScoreTimeline(3).changes(series))

    assert [(g.time, g.kind) for g in goals] == [(300, "goal_away")]


def test_detection_evaluator_counts_misses_and_false_goals(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"match": "m.mp4", "goals": [
        {"minute": "4", "score_after": "1-0", "video_time": "00:06:05"},
        {"minute": "24", "score_after": "1-1", "video_time": "00:25:45"},
    ]}), encoding="utf-8")

    report = GoalDetectionEvaluator(before_seconds=15, after_seconds=75).evaluate(
        GroundTruth.load(path), [370.0, 3000.0]
    )

    assert [g.minute for g in report.matched] == ["4"]
    assert [g.minute for g in report.missed] == ["24"]
    assert report.false_times == (3000.0,)
