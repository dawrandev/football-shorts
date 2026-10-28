from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from fshorts.events.commentary import Word
from fshorts.events.replay_events import TextGenerator

PROMPT = """You write the on-screen text for a football YouTube Short (English).

Match: {home} vs {away}, minute {minute}. Score {before} before the moment, {after} after it.
Moment: {moment}
Commentary around it (seconds relative to the moment):
{lines}

Answer with JSON only:
{{"player": the player at the centre of the moment as the commentator names him, or null,
 "hook": 2-6 words shown at the start to make people keep watching, with one emoji at the end,
 "title": a YouTube title under 70 characters with the player, "{home} vs {away}" and one emoji}}

Style of hooks from popular Shorts: "Incredible solo goal 🤩", "Try and catch Walcott 🥵",
"Wait for Klopp's reaction...", "Dembélé x Ferran again 😤". Titles: "Magic from Dembélé. Finish from
Ferran. ✨", "Troy Parrott's solo goal", "That Swerve🔥". Do not reveal the result in the hook
("goal" is fine for a goal); never invent a name that the commentary does not say."""

MOMENTS = {
    "goal": "a goal", "shot_saved": "a shot saved by the goalkeeper", "near_miss": "a shot that narrowly missed",
    "woodwork": "a shot off the post or bar", "shot_off_target": "a shot just wide or over",
    "shot_blocked": "a blocked shot", "skill": "a skill move or dribble",
}


@dataclass(frozen=True)
class Caption:
    player: str | None
    hook: str
    title: str


class CaptionWriter:
    def __init__(self, generator: TextGenerator, before: float = 15.0, after: float = 10.0) -> None:
        self._generator = generator
        self._before = before
        self._after = after

    def write(self, kind: str, moment: float, words: list[Word], home: str, away: str, before: tuple[int, int],
              after: tuple[int, int], minute: int | None) -> Caption:
        lines = [f"[{w.start - moment:+.0f}s] {w.text}" for w in words
                 if moment - self._before <= w.start <= moment + self._after]
        prompt = PROMPT.format(
            home=home, away=away, minute=minute or "?", before=f"{before[0]}-{before[1]}",
            after=f"{after[0]}-{after[1]}", moment=MOMENTS.get(kind, kind), lines=_join(lines) or "(none)",
        )
        answer = _parse(self._generator.generate(prompt))
        player = answer.get("player") or None
        hook = str(answer.get("hook") or "").strip()
        title = str(answer.get("title") or "").strip() or f"{home} vs {away}"
        return Caption(player if isinstance(player, str) else None, hook, title[:100])


def _join(lines: list[str]) -> str:
    """Words to one line per second so the prompt stays short."""
    merged: dict[str, list[str]] = {}
    for line in lines:
        stamp, word = line.split("] ", 1)
        merged.setdefault(stamp + "]", []).append(word)
    return "\n".join(f"{stamp} {' '.join(words)}" for stamp, words in merged.items())


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


class CaptionStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, Caption]:
        if not self._path.is_file():
            return {}
        return {k: Caption(**v) for k, v in json.loads(self._path.read_text(encoding="utf-8")).items()}

    def save(self, captions: dict[str, Caption]) -> None:
        self._path.write_text(json.dumps({k: asdict(v) for k, v in captions.items()}, ensure_ascii=False, indent=1),
                              encoding="utf-8")
