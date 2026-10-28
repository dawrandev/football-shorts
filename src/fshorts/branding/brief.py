from __future__ import annotations

from bisect import bisect_left

from fshorts.branding.captions import Caption, CaptionStore, CaptionWriter
from fshorts.branding.overlay import BADGES, OverlaySpec
from fshorts.events.commentary import Word
from fshorts.scoreboard import ScoreChange, ScoreReading


class ShortBriefs:
    """Everything a Short shows on screen: teams, score, minute, badge, hook and caption.

    Teams, score and clock come from the score bug readings; the hook, title and scorer from the
    caption writer (an LLM over the commentary), cached per clip so re-renders stay identical.
    """

    def __init__(self, readings: list[ScoreReading], goals: list[ScoreChange], words: list[Word],
                 writer_factory, store: CaptionStore) -> None:
        self._readings = sorted(readings, key=lambda r: r.time)
        self._times = [r.time for r in self._readings]
        self._goals = goals
        self._words = words
        self._writer_factory = writer_factory
        self._writer: CaptionWriter | None = None
        self._store = store
        self._captions = store.load()

    def prepare(self, clips: list[dict]) -> None:
        """Writes every missing caption up front, then frees the language model for the renderers."""
        for clip in clips:
            self.brief(clip)
        if self._writer is not None:
            self._writer = None
            import gc

            import torch

            gc.collect()
            torch.cuda.empty_cache()

    def brief(self, clip: dict) -> tuple[OverlaySpec, Caption]:
        moment = clip["anchor"]
        reading = self._reading_near(moment)
        home, away = (reading.home_code, reading.away_code) if reading else ("HOME", "AWAY")
        before = after = reading.score if reading else (0, 0)
        if clip["kind"] == "goal":
            goal = min(self._goals, key=lambda g: abs(g.time - moment), default=None)
            if goal is not None:
                before, after = goal.before, goal.after
        minute = self._minute(moment)
        caption = self._caption(clip, moment, home, away, before, after, minute)
        kind = clip["kind"] if clip["kind"] == "goal" else clip["label"].split(":")[0].strip()
        player = caption.player or (clip["label"].split(":", 1)[1].strip() if ":" in clip["label"] else None)
        line = f"⚽ {player} {minute}'" if clip["kind"] == "goal" and player else (player or "")
        spec = OverlaySpec(home, away, before, after, minute, moment - clip["start"], clip["end"] - clip["start"],
                           BADGES.get(kind, ""), caption.hook, line)
        return spec, caption

    def _caption(self, clip, moment, home, away, before, after, minute) -> Caption:
        if clip["id"] not in self._captions:
            self._writer = self._writer or self._writer_factory()
            kind = clip["kind"] if clip["kind"] == "goal" else clip["label"].split(":")[0].strip()
            self._captions[clip["id"]] = self._writer.write(kind, moment, self._words, home, away, before, after,
                                                            minute)
            self._store.save(self._captions)
        return self._captions[clip["id"]]

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
