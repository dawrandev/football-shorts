from __future__ import annotations

from bisect import bisect_left

from fshorts.branding.overlay import OverlaySpec
from fshorts.branding.writer import ShortText, ShortTextStore, ShortTextWriter
from fshorts.events.commentary import Word
from fshorts.facts.model import MatchFacts, fold
from fshorts.facts.sheet import MomentFacts, MomentFactsBuilder
from fshorts.scoreboard import ScoreChange, ScoreReading

# Commentary given to the writer for the mood of the moment
COMMENTARY_BEFORE = 12.0
COMMENTARY_AFTER = 8.0


class ShortBriefs:
    """Everything a Short shows on screen: its caption lines, from facts we trust.

    Teams, score and clock come from the score bug readings, names and scorers from the match facts
    (line-ups and goals); the language model only phrases them, and every line it writes is checked.
    Texts are cached per clip so re-renders stay identical.
    """

    def __init__(self, readings: list[ScoreReading], goals: list[ScoreChange], words: list[Word],
                 facts: MatchFacts | None, writer_factory, store: ShortTextStore) -> None:
        self._readings = sorted(readings, key=lambda r: r.time)
        self._times = [r.time for r in self._readings]
        self._goals = sorted(goals, key=lambda g: g.time)
        self._words = words
        self._facts = facts
        self._builder = MomentFactsBuilder(facts)
        self._writer_factory = writer_factory
        self._writer: ShortTextWriter | None = None
        self._store = store
        self._texts = store.load()

    def squad(self) -> set[str]:
        if self._facts is None:
            return set()
        return {part for team in (self._facts.home, self._facts.away) for p in team.players
                for part in fold(p.name).split() + fold(p.full).split()}

    def prepare(self, clips: list[dict]) -> None:
        """Writes every missing text up front, then frees the language model for the renderers."""
        for clip in sorted(clips, key=lambda c: c["start"]):
            self.brief(clip)
        if self._writer is not None:
            self._writer = None
            import gc

            import torch

            gc.collect()
            torch.cuda.empty_cache()

    def brief(self, clip: dict) -> tuple[OverlaySpec, ShortText]:
        text = self._text(clip)
        spec = OverlaySpec(text.format, text.line1, text.line2, clip["anchor"] - clip["start"],
                           clip["end"] - clip["start"])
        return spec, text

    def facts_of(self, clip: dict) -> MomentFacts:
        moment = clip["anchor"]
        reading = self._reading_near(moment)
        home, away = (reading.home_code, reading.away_code) if reading else ("HOME", "AWAY")
        minute = self._minute(moment)
        if clip["kind"] == "goal" and self._goals:
            goal = min(self._goals, key=lambda g: abs(g.time - moment))
            return self._builder.goal(self._goals.index(goal), goal.before, goal.after, minute, home, away)
        kind, _, named = clip["label"].partition(":")
        kind = "skill" if clip["kind"] == "skill" else kind.strip()
        return self._builder.chance(kind, named.strip() or None, minute, home, away)

    def _text(self, clip: dict) -> ShortText:
        if clip["id"] not in self._texts:
            self._writer = self._writer or self._writer_factory(self.squad())
            self._texts[clip["id"]] = self._writer.write(self.facts_of(clip), self._commentary(clip["anchor"]))
            self._store.save(self._texts)
        return self._texts[clip["id"]]

    def _commentary(self, moment: float) -> str:
        words = [w.text for w in self._words if moment - COMMENTARY_BEFORE <= w.start <= moment + COMMENTARY_AFTER]
        return " ".join(words)

    def _reading_near(self, time: float) -> ScoreReading | None:
        if not self._readings:
            return None
        i = bisect_left(self._times, time - 2)   # the last score shown before the moment
        return self._readings[min(i, len(self._readings) - 1)]

    def _minute(self, time: float) -> int | None:
        """Match minute as broadcast clocks count it: 28:04 on the clock is the 29th minute."""
        clocked = [r for r in self._readings if r.clock_seconds is not None and abs(r.time - time) <= 30]
        if not clocked:
            return None
        nearest = min(clocked, key=lambda r: abs(r.time - time))
        return int((nearest.clock_seconds + (time - nearest.time)) // 60) + 1
