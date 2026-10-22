from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fshorts.events.candidate import Candidate


def parse_timestamp(value: str) -> float:
    seconds = 0.0
    for part in value.split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


@dataclass(frozen=True)
class LabelledGoal:
    minute: str
    score_after: str
    video_time: float


@dataclass(frozen=True)
class GroundTruth:
    match: str
    goals: tuple[LabelledGoal, ...]

    @classmethod
    def load(cls, path: Path) -> GroundTruth:
        raw = json.loads(path.read_text(encoding="utf-8"))
        unlabelled = [g["minute"] for g in raw["goals"] if not g.get("video_time")]
        if unlabelled:
            raise ValueError(f"{path.name}: goals without video_time: {unlabelled}")
        return cls(
            match=raw["match"],
            goals=tuple(
                LabelledGoal(g["minute"], g["score_after"], parse_timestamp(g["video_time"]))
                for g in raw["goals"]
            ),
        )


@dataclass(frozen=True)
class RecallReport:
    found: tuple[LabelledGoal, ...]
    missed: tuple[LabelledGoal, ...]
    candidate_count: int

    @property
    def recall(self) -> float:
        total = len(self.found) + len(self.missed)
        return len(self.found) / total if total else 1.0


@dataclass(frozen=True)
class DetectionReport:
    matched: tuple[LabelledGoal, ...]
    missed: tuple[LabelledGoal, ...]
    false_times: tuple[float, ...]


class GoalDetectionEvaluator:
    """One-to-one matching of detected goal times to labelled goals.

    The score bug changes after the goal (instantly, or after the replay when the
    bug is hidden), so a detection may lag the label by up to `after_seconds`.
    """

    def __init__(self, before_seconds: float = 15.0, after_seconds: float = 75.0) -> None:
        self._before = before_seconds
        self._after = after_seconds

    def evaluate(self, truth: GroundTruth, detected_times: list[float]) -> DetectionReport:
        unused = sorted(detected_times)
        matched, missed = [], []
        for goal in truth.goals:
            hit = next(
                (t for t in unused if goal.video_time - self._before <= t <= goal.video_time + self._after),
                None,
            )
            if hit is None:
                missed.append(goal)
            else:
                matched.append(goal)
                unused.remove(hit)
        return DetectionReport(tuple(matched), tuple(missed), tuple(unused))


class GoalRecallEvaluator:
    """A goal counts as found when some candidate lies within the tolerance window around it."""

    def __init__(self, before_seconds: float = 20.0, after_seconds: float = 45.0) -> None:
        # Reactions (roar, "goal!") come at or after the goal, so the window leans forward
        self._before = before_seconds
        self._after = after_seconds

    def evaluate(self, truth: GroundTruth, candidates: list[Candidate]) -> RecallReport:
        found, missed = [], []
        for goal in truth.goals:
            hit = any(
                goal.video_time - self._before <= c.time <= goal.video_time + self._after
                for c in candidates
            )
            (found if hit else missed).append(goal)
        return RecallReport(tuple(found), tuple(missed), len(candidates))
