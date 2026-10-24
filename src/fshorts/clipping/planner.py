from __future__ import annotations

from dataclasses import dataclass, replace

from fshorts.broadcast import BroadcastTimeline, Replay
from fshorts.config import ClipConfig
from fshorts.events import Candidate
from fshorts.events.replay_events import ReplayEvent
from fshorts.scoreboard import ScoreChange, ScoreReading

# A gap between score readings longer than this means the bug was hidden (replay, close-ups)
HIDDEN_BUG_SECONDS = 3.0
# When the bug updates within this many seconds of the last old reading, its change time is the goal time
PROMPT_UPDATE_SECONDS = 15.0
# Commentary cue strong enough to place a goal whose score bug was hidden
STRONG_CUE_SCORE = 2.0
# Goals always outrank chances
GOAL_SCORE = 1000.0
# Replays this long after a goal still belong to it (celebration, alternate angles, before the restart)
GOAL_REPLAY_WINDOW = 150.0
# At least this much build-up must stay when a clip start is pushed out of a replay
MIN_BUILD_UP = 8.0
# How long a chance clip keeps running after the action, unless the replay starts first
CHANCE_AFTER = 4.0
REPLAY_MAX = 40.0
# Ranking of replayed moments: a near miss is the best chance clip
EVENT_SCORES = {
    "woodwork": 5.0, "near_miss": 4.5, "shot_saved": 4.0, "skill": 3.5, "shot_off_target": 3.0, "shot_blocked": 2.0,
}


@dataclass(frozen=True)
class ClipPlan:
    kind: str            # goal, goal_replay, chance, chance_replay, skill, skill_replay
    anchor: float        # best estimate of the moment itself
    start: float
    end: float
    score: float
    label: str
    floor: float = 0.0              # snapping may not move the edges past these (a replay, another shot)
    ceiling: float = float("inf")

    @property
    def duration(self) -> float:
        return self.end - self.start


class ClipPlanner:
    """Turns confirmed goals and replayed moments into non-overlapping clip windows.

    With a broadcast timeline, chances come from the replays the director chose to show; without
    one, from ranked commentary and audio candidates.
    """

    def __init__(self, config: ClipConfig) -> None:
        self._config = config

    def plan(
        self,
        goals: list[ScoreChange],
        readings: list[ScoreReading],
        candidates: list[Candidate],
        duration: float,
        timeline: BroadcastTimeline | None = None,
        events: list[ReplayEvent] | None = None,
    ) -> list[ClipPlan]:
        times = sorted(r.time for r in readings)
        goal_plans = [self._goal_plan(goal, readings, times, candidates) for goal in goals]
        if timeline is not None:
            goal_plans = [self._live_start(p, timeline) for p in goal_plans]
        plans = list(goal_plans)
        if timeline is not None and events is not None:
            plans += self._goal_replay_plans(goal_plans, events)
            plans += self._event_plans(events, goal_plans, timeline, plans)
        else:
            # The score bug is on screen only while the match is played; studio talk before and after is not
            in_play = [c for c in candidates if not times or times[0] <= c.time <= times[-1]]
            plans += self._chance_plans(in_play, goal_plans)
        return sorted((self._clamp(p, duration) for p in plans), key=lambda p: p.start)

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

    @staticmethod
    def _live_start(plan: ClipPlan, timeline: BroadcastTimeline) -> ClipPlan:
        """Opens the clip on live play: never on the tail of a replay or on a bench or crowd shot."""
        latest = plan.anchor - MIN_BUILD_UP
        floor = max(
            (end for start, end in timeline.hidden_stretches() if start < plan.start + 1 and end <= latest),
            default=0.0,
        )
        start = max(plan.start, floor)
        live = timeline.first_on_air_play(start, within=max(0.0, latest - start))
        return replace(plan, start=live if live is not None else start, floor=floor)

    @staticmethod
    def _goal_replay_plans(goal_plans: list[ClipPlan], events: list[ReplayEvent]) -> list[ClipPlan]:
        plans = []
        for goal in goal_plans:
            replays = [e.replay for e in events if goal.end - 1 <= e.replay.start <= goal.anchor + GOAL_REPLAY_WINDOW]
            if replays:
                start, end = replays[0].start, min(replays[-1].end, replays[0].start + REPLAY_MAX)
                plans.append(ClipPlan("goal_replay", goal.anchor, start, end, GOAL_SCORE - 1, goal.label,
                                      floor=start, ceiling=end))
        return plans

    def _event_plans(
        self, events: list[ReplayEvent], goal_plans: list[ClipPlan], timeline: BroadcastTimeline,
        taken: list[ClipPlan],
    ) -> list[ClipPlan]:
        goal_times = [g.anchor for g in goal_plans]
        usable = [
            e for e in events
            if (e.is_chance or e.is_skill) and not e.recap
            # Replays right before and after a goal show that goal (or the foul that gave the penalty)
            and not any(g - 30 <= e.replay.start <= g + GOAL_REPLAY_WINDOW for g in goal_times)
        ]
        plans: list[ClipPlan] = []
        moments = 0
        for event in sorted(usable, key=lambda e: EVENT_SCORES[e.kind], reverse=True):
            live, again = self._event_pair(event, timeline)
            if any(self._overlaps(live, other) for other in taken + plans):
                continue
            plans += [live, again]
            moments += 1
            if moments == self._config.max_chances:
                break
        return plans

    def _event_pair(self, event: ReplayEvent, timeline: BroadcastTimeline) -> tuple[ClipPlan, ClipPlan]:
        replay: Replay = event.replay
        anchor = replay.event if replay.event is not None else replay.start - 2.0
        kind = "skill" if event.kind == "skill" else "chance"
        label = f"{event.kind}: {event.player}" if event.player else event.kind
        score = EVENT_SCORES[event.kind]
        live = ClipPlan(kind, anchor, anchor - self._config.pre_seconds, min(anchor + CHANCE_AFTER, replay.start),
                        score, label, ceiling=replay.start)
        again = ClipPlan(f"{kind}_replay", anchor, replay.start, min(replay.end, replay.start + REPLAY_MAX),
                         score - 0.5, label, floor=replay.start, ceiling=replay.end)
        return self._live_start(live, timeline), again

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
        return replace(plan, start=max(0.0, plan.start), end=min(duration, plan.end))
