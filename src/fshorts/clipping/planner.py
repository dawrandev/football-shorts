from __future__ import annotations

from dataclasses import dataclass

from fshorts.config import ClipConfig
from fshorts.events import Candidate
from fshorts.scoreboard import ScoreChange, ScoreReading

# A gap between score readings longer than this means the bug was hidden (replay, close-ups)
HIDDEN_BUG_SECONDS = 3.0
# When the bug updates within this many seconds of the last old reading, its change time is the goal time
PROMPT_UPDATE_SECONDS = 15.0
# Commentary cue strong enough to place a goal whose score bug was hidden
STRONG_CUE_SCORE = 2.0
# Goals always outrank chances
GOAL_SCORE = 1000.0


@dataclass(frozen=True)
class ClipPlan:
    kind: str            # "goal" or "chance"
    anchor: float        # best estimate of the moment itself
    start: float
    end: float
    score: float
    label: str

    @property
    def duration(self) -> float:
        return self.end - self.start


class ClipPlanner:
    """Turns confirmed goals and ranked candidates into non-overlapping clip windows."""

    def __init__(self, config: ClipConfig) -> None:
        self._config = config

    def plan(
        self,
        goals: list[ScoreChange],
        readings: list[ScoreReading],
        candidates: list[Candidate],
        duration: float,
    ) -> list[ClipPlan]:
        times = sorted(r.time for r in readings)
        goal_plans = [self._goal_plan(goal, readings, times, candidates) for goal in goals]
        # The score bug is on screen only while the match is played; studio talk before and after is not
        in_play = [c for c in candidates if not times or times[0] <= c.time <= times[-1]]
        chance_plans = self._chance_plans(in_play, goal_plans)
        plans = [self._clamp(p, duration) for p in goal_plans + chance_plans]
        return sorted(plans, key=lambda p: p.start)

    def _goal_plan(
        self, goal: ScoreChange, readings: list[ScoreReading], times: list[float], candidates: list[Candidate]
    ) -> ClipPlan:
        anchor = self._goal_moment(goal, readings, candidates)
        end = anchor + self._config.goal_post_seconds
        if self._config.include_replay:
            end = max(end, min(self._bug_back_time(anchor, times), anchor + self._config.goal_post_seconds
                               + self._config.replay_max_seconds))
        home, away = goal.after
        return ClipPlan("goal", anchor, anchor - self._config.goal_pre_seconds, end, GOAL_SCORE, f"{home}-{away}")

    @staticmethod
    def _goal_moment(goal: ScoreChange, readings: list[ScoreReading], candidates: list[Candidate]) -> float:
        last_old = max((r.time for r in readings if r.score == goal.before and r.time < goal.time), default=goal.time)
        if goal.time - last_old <= PROMPT_UPDATE_SECONDS:
            return goal.time
        cues = [
            c.time for c in candidates
            if last_old <= c.time <= goal.time and "commentary" in c.sources and c.score >= STRONG_CUE_SCORE
        ]
        return min(cues) if cues else last_old + 5.0

    @staticmethod
    def _bug_back_time(anchor: float, times: list[float]) -> float:
        """End of the first hidden-bug stretch that starts shortly after the goal."""
        for previous, current in zip(times, times[1:]):
            if previous < anchor - 5:
                continue
            if previous > anchor + 20:
                break
            if current - previous > HIDDEN_BUG_SECONDS:
                return current
        return anchor

    def _chance_plans(self, candidates: list[Candidate], goal_plans: list[ClipPlan]) -> list[ClipPlan]:
        plans: list[ClipPlan] = []
        for candidate in sorted(candidates, key=lambda c: c.score, reverse=True):
            plan = ClipPlan(
                "chance",
                candidate.time,
                candidate.time - self._config.pre_seconds,
                candidate.time + self._config.post_seconds,
                candidate.score,
                ", ".join(candidate.details[:3]) or "+".join(candidate.sources),
            )
            if any(self._overlaps(plan, other) for other in goal_plans + plans):
                continue
            plans.append(plan)
            if len(plans) == self._config.max_chances:
                break
        return plans

    @staticmethod
    def _overlaps(a: ClipPlan, b: ClipPlan) -> bool:
        return a.start < b.end and b.start < a.end

    @staticmethod
    def _clamp(plan: ClipPlan, duration: float) -> ClipPlan:
        return ClipPlan(plan.kind, plan.anchor, max(0.0, plan.start), min(duration, plan.end), plan.score, plan.label)
