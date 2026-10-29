from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from fshorts.branding.examples import EXAMPLES
from fshorts.branding.rules import MAX_PUNCH_WORDS, MAX_TITLE_CHARS, MAX_TITLE_WORDS, problems
from fshorts.events.replay_events import TextGenerator
from fshorts.facts.sheet import MomentFacts

FORMATS = ("label", "teaser", "question", "two_beat")
# The second line lands at the moment, so it may not be one more teaser
TEASE = re.compile(r"(wait|watch|something|keep|look)\b", re.IGNORECASE)

PROMPT = """You write the on-screen text of a football YouTube Short, in the style of the most viewed
Shorts of UEFA, the Premier League, PSG and Real Madrid.

FACTS about this moment (state nothing beyond them):
{facts}
{commentary}
Formats:
- label: one short line shown while the play builds up. {label}
- teaser: makes people wait for the moment, never tells the result. {teaser}
- question: asks the viewer something the clip answers. {question}
- two_beat: line1 sets it up before the moment, line2 (1-3 words) lands at the moment. {two_beat}

Rules:
- English, sentence case, at most 7 words per line, at most one emoji, at the end of a line.
  One word in CAPITALS for emphasis is fine ("out of NOWHERE").
- Use names only from FACTS, written exactly as there; otherwise say "this", "he" or nothing.
- Use player names more than team names. Never invent details (headers, distances, records, debuts).
- Tease, do not describe: "Wait for it" beats "Ronaldo shoots from outside the box".
- When FACTS has a "story", the best options are built on it (a hat-trick, a late equaliser).
- Plain, natural English a fan would type; no made-up or odd words.

Answer with JSON only:
{{"options": [4 objects {{"format": "label" | "teaser" | "question" | "two_beat", "line1": "...", "line2": "..." or null}},
              one of each format, best first],
 "title": "YouTube title under 70 characters: emotion + player + {home} vs {away}, one emoji"}}"""


@dataclass(frozen=True)
class ShortText:
    format: str
    line1: str
    line2: str | None
    title: str
    player: str | None

    def to_dict(self) -> dict:
        return asdict(self)


class ShortTextWriter:
    """Asks a language model for caption options and keeps the first one the facts support."""

    def __init__(self, generator: TextGenerator, squad: set[str]) -> None:
        self._generator = generator
        self._squad = squad
        self._recent: list[str] = []
        self._used: set[str] = set()   # lines already on a Short of this match

    def write(self, facts: MomentFacts, commentary: str = "") -> ShortText:
        group = "goal" if facts.kind == "goal" else "skill" if facts.kind == "skill" else "chance"
        examples = EXAMPLES[group]
        prompt = PROMPT.format(
            facts=json.dumps(facts.to_dict(), ensure_ascii=False),
            commentary=f"Commentary around it, for the mood only:\n{commentary}\n" if commentary else "",
            home=facts.home, away=facts.away,
            **{f: "Examples: " + " | ".join(examples[f]) for f in FORMATS},
        )
        answer = _parse(self._generator.generate(prompt))
        options = [o for o in answer.get("options", []) if isinstance(o, dict)]
        chosen = self._choose(options, facts)
        if chosen is None and options:
            # One more try, told what was wrong with the first options
            answer = _parse(self._generator.generate(prompt + RETRY.format(rejected=self._rejected(options, facts))))
            options = [o for o in answer.get("options", []) if isinstance(o, dict)]
            chosen = self._choose(options, facts)
        chosen = chosen or (fallback_line(facts), None)
        title = str(answer.get("title") or "").strip()
        if not title or problems(title, facts, self._squad, MAX_TITLE_WORDS) or len(title) > MAX_TITLE_CHARS:
            title = fallback_title(facts)
        line1, line2 = chosen
        fmt = "two_beat" if line2 else "label"
        for option in options:
            if option.get("line1") == line1:
                fmt = option.get("format") if option.get("format") in FORMATS else fmt
        self._recent = (self._recent + [fmt])[-2:]
        self._used |= {_key(line1)} | ({_key(line2)} if line2 else set())
        return ShortText(fmt, line1, line2, title, facts.player or facts.keeper)

    def _choose(self, options: list[dict], facts: MomentFacts) -> tuple[str, str | None] | None:
        valid = []
        for option in options:
            line1, line2 = _lines(option)
            if line1 and not self._problems(line1, line2, facts):
                valid.append((option.get("format"), line1, line2))
        if not valid:
            return None
        # Options come best first; only a third Short in a row in the same format gives way
        if len(self._recent) == 2 and len(set(self._recent)) == 1:
            valid = [v for v in valid if v[0] != self._recent[0]] + [v for v in valid if v[0] == self._recent[0]]
        _, line1, line2 = valid[0]
        return line1, line2

    def _problems(self, line1: str, line2: str | None, facts: MomentFacts) -> list[str]:
        found = problems(line1, facts, self._squad)
        if line2:
            found += problems(line2, facts, self._squad, MAX_PUNCH_WORDS)
            if TEASE.match(line2) or " vs " in line2.lower():
                found.append("punchline teases instead of landing")
        found += [f"already used '{line}'" for line in (line1, line2) if line and _key(line) in self._used]
        return found

    def _rejected(self, options: list[dict], facts: MomentFacts) -> str:
        rows = []
        for option in options:
            line1, line2 = _lines(option)
            if line1:
                text = line1 + (f" / {line2}" if line2 else "")
                rows.append(f"- {text}: {'; '.join(self._problems(line1, line2, facts))}")
        return "\n".join(rows)


RETRY = """

All of these options were rejected:
{rejected}
Write 4 new options that avoid these problems, same JSON."""


def _lines(option: dict) -> tuple[str, str | None]:
    return str(option.get("line1") or "").strip(), str(option.get("line2") or "").strip() or None


def fallback_line(facts: MomentFacts) -> str:
    """A safe line when no option passes the checks, built on the story when there is one."""
    who = facts.player
    if facts.kind == "goal":
        if not who:
            return "Wait for it… 👀"
        if facts.nth_goal == 3:
            return f"{who} hat-trick 🤯"
        if facts.equaliser:
            return f"{who} levels it 🤯"
        if facts.penalty:
            return f"{who} from the spot 🎯"
        if facts.go_ahead and facts.player_team:
            return f"{who} puts {facts.player_team} ahead 🔥"
        return f"{who} again 🔥" if (facts.nth_goal or 0) >= 2 else f"{who} 🤯"
    if facts.kind == "shot_saved" and facts.keeper:
        return f"{facts.keeper} says no ✋"
    if facts.kind == "skill" and who:
        return f"{who} magic 🪄"
    return "So close… 😮"


def fallback_title(facts: MomentFacts) -> str:
    # A save belongs to the keeper; the shooter's name there would credit the wrong man
    who = facts.keeper if facts.kind == "shot_saved" else facts.player
    what = {"goal": "What a goal", "shot_saved": "What a save", "skill": "Skills"}.get(facts.kind, "So close")
    return f"{what}{' ' + who if who else ''}! {facts.home} vs {facts.away} ⚽"[:MAX_TITLE_CHARS]


def _key(line: str) -> str:
    return re.sub(r"[^a-z ]", "", line.lower()).strip()


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


class ShortTextStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, ShortText]:
        if not self._path.is_file():
            return {}
        return {k: ShortText(**v) for k, v in json.loads(self._path.read_text(encoding="utf-8")).items()}

    def save(self, texts: dict[str, ShortText]) -> None:
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in texts.items()}, ensure_ascii=False, indent=1),
                              encoding="utf-8")
