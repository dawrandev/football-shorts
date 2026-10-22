import json

import pytest

from fshorts.evaluation import GoalRecallEvaluator, GroundTruth, parse_timestamp
from fshorts.events import Candidate


def write_truth(tmp_path, goals):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"match": "m.mp4", "goals": goals}), encoding="utf-8")
    return path


def test_parse_timestamp():
    assert parse_timestamp("01:02:03") == 3723
    assert parse_timestamp("05:30") == 330


def test_unlabelled_goals_rejected(tmp_path):
    path = write_truth(tmp_path, [{"minute": "4", "score_after": "1-0", "video_time": None}])

    with pytest.raises(ValueError, match="without video_time"):
        GroundTruth.load(path)


def test_recall_counts_goals_inside_window(tmp_path):
    truth = GroundTruth.load(write_truth(tmp_path, [
        {"minute": "4", "score_after": "1-0", "video_time": "00:05:00"},
        {"minute": "24", "score_after": "1-1", "video_time": "00:25:00"},
    ]))
    candidates = [Candidate(320.0, 1.0, ("audio",)), Candidate(1600.0, 1.0, ("audio",))]

    report = GoalRecallEvaluator(before_seconds=20, after_seconds=45).evaluate(truth, candidates)

    assert report.recall == 0.5
    assert [g.minute for g in report.missed] == ["24"]
