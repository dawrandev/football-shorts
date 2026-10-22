from __future__ import annotations

from dataclasses import dataclass

from fshorts.scoreboard.reading import ScoreReading


@dataclass(frozen=True)
class ScoreChange:
    """A confirmed change of the on-screen score.

    time is the first sample that showed the new score; the goal itself happens
    shortly before, usually within the replay/celebration that follows.
    """

    time: float
    before: tuple[int, int]
    after: tuple[int, int]

    @property
    def kind(self) -> str:
        home_delta = self.after[0] - self.before[0]
        away_delta = self.after[1] - self.before[1]
        if (home_delta, away_delta) == (1, 0):
            return "goal_home"
        if (home_delta, away_delta) == (0, 1):
            return "goal_away"
        if home_delta <= 0 and away_delta <= 0:
            return "revert"
        return "jump"

    def to_dict(self) -> dict:
        return {"time": self.time, "before": list(self.before), "after": list(self.after), "kind": self.kind}


class ScoreTimeline:
    """Debounces noisy per-second readings into confirmed score changes.

    A new score is accepted only after `confirmations` consecutive readings agree.
    Seconds without a readable bug (replays, close-ups) are skipped rather than
    breaking the streak.
    """

    def __init__(self, confirmations: int = 3) -> None:
        self._confirmations = confirmations

    def changes(self, readings: list[ScoreReading]) -> list[ScoreChange]:
        current: tuple[int, int] | None = None
        pending: list[ScoreReading] = []
        changes: list[ScoreChange] = []
        for reading in sorted(readings, key=lambda r: r.time):
            if reading.score == current:
                pending = []
                continue
            if pending and pending[0].score != reading.score:
                pending = []
            pending.append(reading)
            if len(pending) < self._confirmations:
                continue
            if current is not None:
                changes.append(ScoreChange(pending[0].time, current, reading.score))
            current = reading.score
            pending = []
        return changes


class GoalExtractor:
    """Goal events from score changes; a revert (VAR) cancels the latest goal it undoes."""

    def goals(self, changes: list[ScoreChange]) -> list[ScoreChange]:
        goals: list[ScoreChange] = []
        for change in changes:
            if change.kind in ("goal_home", "goal_away"):
                goals.append(change)
            elif change.kind == "revert":
                goals = [g for g in goals if not self._undone_by(g, change)]
        return goals

    @staticmethod
    def _undone_by(goal: ScoreChange, revert: ScoreChange) -> bool:
        return goal.time < revert.time and goal.after == revert.before and goal.before == revert.after
