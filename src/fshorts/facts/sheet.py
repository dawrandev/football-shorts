from __future__ import annotations

from dataclasses import asdict, dataclass

from fshorts.facts.model import MatchFacts, Player

# Minute from which a goal counts as late
LATE_MINUTE = 80
CHANCE_KINDS = ("shot_saved", "near_miss", "woodwork", "shot_off_target", "shot_blocked")


@dataclass(frozen=True)
class MomentFacts:
    """What is known for sure about one moment; the text writer may only use these."""

    kind: str                     # goal, shot_saved, near_miss, woodwork, shot_off_target, shot_blocked, skill
    home: str                     # team names as captions write them: "Portugal"
    away: str
    minute: int | None
    player: str | None = None     # the player at the centre (scorer, shooter or dribbler), short name
    player_team: str | None = None
    keeper: str | None = None     # the goalkeeper who made the save, short name
    score_after: str | None = None    # "2-1" after a goal
    nth_goal: int | None = None       # the scorer's 1st, 2nd, 3rd goal of the match
    penalty: bool = False
    free_kick: bool = False
    own_goal: bool = False
    equaliser: bool = False
    go_ahead: bool = False
    late: bool = False

    def story(self) -> list[str]:
        """The angles worth a caption, in plain words, strongest first."""
        found = []
        if self.kind == "goal":
            if self.nth_goal == 3:
                found.append("this goal completes his hat-trick")
            elif self.nth_goal == 2:
                found.append("his second goal of the match")
            if self.penalty:
                found.append("scored from the penalty spot")
            if self.own_goal:
                found.append("an own goal")
            if self.equaliser:
                found.append(("late " if self.late else "") + f"equaliser, {self.score_after}")
            elif self.go_ahead:
                found.append(("late " if self.late else "") + f"puts {self.player_team} in front, {self.score_after}")
            elif self.late:
                found.append(f"late goal, {self.score_after}")
        elif self.keeper and self.kind == "shot_saved":
            found.append(f"{self.keeper} makes the save")
        if self.minute and self.minute >= 85 and self.kind != "goal":
            found.append("in the final minutes")
        return found

    def names(self) -> set[str]:
        return {n for n in (self.player, self.keeper, self.home, self.away, self.player_team) if n}

    def to_dict(self) -> dict:
        data = {k: v for k, v in asdict(self).items() if v not in (None, False)}
        if self.story():
            data["story"] = self.story()
        return data


class MomentFactsBuilder:
    """Joins what the broadcast told us (score bug, replay label) with the match facts (line-ups, scorers)."""

    def __init__(self, facts: MatchFacts | None) -> None:
        self._facts = facts

    def goal(self, index: int, before: tuple[int, int], after: tuple[int, int], minute: int | None,
             home_code: str, away_code: str, free_kick: bool = False) -> MomentFacts:
        home, away = self._team_names(home_code, away_code)
        scoring_home = after[0] > before[0]
        team_code = home_code if scoring_home else away_code
        base = dict(kind="goal", home=home, away=away, minute=minute, score_after=f"{after[0]}-{after[1]}",
                    player_team=home if scoring_home else away, late=bool(minute and minute >= LATE_MINUTE),
                    equaliser=after[0] == after[1], go_ahead=_go_ahead(before, after), free_kick=free_kick)
        goal = self._facts.goal(index) if self._facts else None
        # The facts list and our goal list must agree on who scored, or the name is not trusted
        if goal is None or goal.team != team_code:
            return MomentFacts(**base)
        scorer = self._facts.scorer(goal)
        name = self._facts.caption_name(scorer.player) if scorer else goal.scorer
        return MomentFacts(**base, player=name, nth_goal=self._facts.goals_by(goal.full, index) or None,
                           penalty=goal.penalty, own_goal=goal.own_goal)

    def chance(self, kind: str, named: str | None, minute: int | None, home_code: str,
               away_code: str) -> MomentFacts:
        home, away = self._team_names(home_code, away_code)
        base = dict(kind=kind, home=home, away=away, minute=minute)
        resolved = self._facts.resolve(named) if self._facts else None
        if resolved is None:
            return MomentFacts(**base)
        team = home if resolved.team == home_code else away
        if kind == "shot_saved" and resolved.player.is_goalkeeper:
            # The commentator named the keeper: the save is his, the shooter stays unnamed
            return MomentFacts(**base, keeper=self._facts.caption_name(resolved.player))
        keeper = self._keeper_against(resolved.team) if kind == "shot_saved" else None
        if kind == "skill" or resolved.player.position != "GK":
            return MomentFacts(**base, player=self._facts.caption_name(resolved.player), player_team=team,
                               keeper=self._facts.caption_name(keeper) if keeper else None)
        return MomentFacts(**base)

    def _keeper_against(self, team_code: str) -> Player | None:
        other = self._facts.away if self._facts.home.code == team_code else self._facts.home
        return next((p for p in other.players if p.is_goalkeeper and p.starter), None)

    def _team_names(self, home_code: str, away_code: str) -> tuple[str, str]:
        if self._facts is None:
            return home_code, away_code
        names = {self._facts.home.code: self._facts.home.name, self._facts.away.code: self._facts.away.name}
        return names.get(home_code, home_code), names.get(away_code, away_code)


def _go_ahead(before: tuple[int, int], after: tuple[int, int]) -> bool:
    """The goal puts the scoring side in front."""
    home_scored = after[0] > before[0]
    return (after[0] > after[1] and before[0] <= before[1]) if home_scored else (after[1] > after[0] and before[1] <= before[0])

