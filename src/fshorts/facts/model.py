from __future__ import annotations

import difflib
import json
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

# A commentary name this close to one alias (and clearly closer than to any other) is that player
MIN_NAME_RATIO = 0.8
GOALKEEPER = "GK"
# Surname particles that stay with the surname, and suffixes that are not a surname at all
PARTICLES = {"de", "da", "di", "do", "dos", "das", "del", "della", "van", "von", "der", "den", "la", "le", "ter"}
SUFFIXES = {"junior", "jr", "neto", "filho"}
# Teams whose players are named family name first ("Son Heung-min", "Hong Chul")
FAMILY_NAME_FIRST = {"KOR", "PRK", "JPN", "CHN", "VIE"}
# Lusophone teams, where two-word names are used whole
GIVEN_NAME_TEAMS = {"POR", "BRA"}


def fold(text: str) -> str:
    """Lowercase ASCII form: commentators and Whisper drop accents ("Patricio", "Vazquez")."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().replace("-", " ").replace(".", " ").split())


@dataclass(frozen=True)
class Player:
    name: str          # how the broadcast and the line-up show him: "Cristiano Ronaldo", "Nacho"
    full: str          # page title: "Nacho", "Cédric Soares"
    number: int
    position: str      # GK, CB, CM, CF ...
    starter: bool = True

    @property
    def short(self) -> str:
        """The name a caption uses: "Costa", "De Gea", "Di María", "Vinícius", "Son Heung-min"."""
        parts = self.name.split()
        if len(parts) == 1 or any("-" in p for p in parts[1:]):
            return self.name   # one-word names, and Korean names whose family name comes first
        if fold(parts[-1]) in SUFFIXES:
            return parts[0]
        surname = [parts[-1]]
        for word in reversed(parts[1:-1]):
            if fold(word) not in PARTICLES:
                break
            surname.insert(0, word)
        surname[0] = surname[0][0].upper() + surname[0][1:]
        return " ".join(surname)

    @property
    def is_goalkeeper(self) -> bool:
        return self.position == GOALKEEPER

    def aliases(self) -> set[str]:
        names = {fold(self.name), fold(self.full), fold(self.short)}
        for name in (self.name, self.full):
            parts = fold(name).split()
            if len(parts) > 1:
                # "Costa", "Diego Costa", and the first word for "Vinícius Júnior" or "Son Heung-min"
                names.add(parts[-1])
                names.add(" ".join(parts[-2:]))
                names.add(parts[0])
        return {n for n in names if n}


@dataclass(frozen=True)
class Team:
    code: str
    name: str
    players: list[Player]


@dataclass(frozen=True)
class GoalFact:
    team: str          # code of the team the goal counts for
    scorer: str        # name as shown in the match box ("Ronaldo")
    full: str
    minute: int
    added: int = 0
    note: str = ""     # "pen.", "o.g." or ""

    @property
    def own_goal(self) -> bool:
        return self.note.startswith("o.g")

    @property
    def penalty(self) -> bool:
        return self.note.startswith("pen")


@dataclass(frozen=True)
class Resolved:
    player: Player
    team: str


@dataclass(frozen=True)
class MatchFacts:
    home: Team
    away: Team
    goals: list[GoalFact] = field(default_factory=list)

    def resolve(self, name: str | None, team: str | None = None) -> Resolved | None:
        """The squad player a commentary name means, or None when unknown or ambiguous."""
        if not name:
            return None
        wanted = fold(name)
        scored: list[tuple[float, Resolved]] = []
        for side in (self.home, self.away):
            if team and side.code != team:
                continue
            for player in side.players:
                best = max(difflib.SequenceMatcher(None, wanted, alias).ratio() for alias in player.aliases())
                scored.append((best, Resolved(player, side.code)))
        scored.sort(key=lambda s: s[0], reverse=True)
        if not scored or scored[0][0] < MIN_NAME_RATIO:
            return None
        # "Silva" fits Bernardo, André and David Silva equally: naming any of them would be a guess
        if len(scored) > 1 and scored[1][0] >= scored[0][0] - 0.05 and scored[1][1].player != scored[0][1].player:
            return None
        return scored[0][1]

    def caption_name(self, player: Player) -> str:
        """The short name unless it is shared in this match ("Silva") or the family name comes first."""
        team = next((t for t in (self.home, self.away) if player in t.players), None)
        if team is not None and team.code in FAMILY_NAME_FIRST:
            return player.name
        if team is not None and team.code in GIVEN_NAME_TEAMS and len(player.name.split()) == 2:
            return player.name   # "Thiago Silva", "João Mário": the surname alone is not how they are known
        others = [p for t in (self.home, self.away) for p in t.players if p != player]
        return player.name if any(fold(p.short) == fold(player.short) for p in others) else player.short

    def goal(self, index: int) -> GoalFact | None:
        """The match's goals in scoring order; our goal clips come in the same order."""
        return self.goals[index] if 0 <= index < len(self.goals) else None

    def scorer(self, goal: GoalFact) -> Resolved | None:
        return self.resolve(goal.full, goal.team) or self.resolve(goal.scorer, goal.team)

    def goals_by(self, full: str, upto: int) -> int:
        """How many of the first `upto` + 1 goals this player scored (his 1st, 2nd, 3rd...)."""
        return sum(1 for g in self.goals[:upto + 1] if g.full == full and not g.own_goal)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MatchFacts:
        def team(t: dict) -> Team:
            return Team(t["code"], t["name"], [Player(**p) for p in t["players"]])

        return cls(team(data["home"]), team(data["away"]), [GoalFact(**g) for g in data["goals"]])

    @classmethod
    def load(cls, path: Path) -> MatchFacts:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
