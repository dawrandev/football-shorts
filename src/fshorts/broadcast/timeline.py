from __future__ import annotations

from dataclasses import dataclass

# Camera views a highlight may be built from
PLAY_VIEWS = ("wide", "goalmouth")
# Views that never belong in a clip, even with the score bug on screen
OFF_PLAY_VIEWS = ("crowd", "logo")


@dataclass(frozen=True)
class Replay:
    start: float
    end: float
    event: float | None   # last live play-view moment before the replay: the action it shows

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "event": self.event}

    @classmethod
    def from_dict(cls, raw: dict) -> Replay:
        return cls(raw["start"], raw["end"], raw["event"])


@dataclass(frozen=True)
class BroadcastTimeline:
    """Per-frame broadcast state: is the score bug on screen, and which camera view is shown.

    The host broadcaster hides the bug during replays and keeps it during live close-ups,
    so a hidden-bug stretch is a replay (or a graphic) and the director only replays what mattered.
    """

    fps: float
    bug_visible: tuple[bool, ...]
    views: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"fps": self.fps, "bug_visible": [int(v) for v in self.bug_visible], "views": list(self.views)}

    @classmethod
    def from_dict(cls, raw: dict) -> BroadcastTimeline:
        return cls(raw["fps"], tuple(bool(v) for v in raw["bug_visible"]), tuple(raw["views"]))

    def _index(self, time: float) -> int:
        return min(max(int(round(time * self.fps)), 0), len(self.views) - 1)

    def _time(self, index: int) -> float:
        return index / self.fps

    def hidden_stretches(self, min_seconds: float = 0.0) -> list[tuple[float, float]]:
        stretches, start = [], None
        for i, visible in enumerate(self.bug_visible + (True,)):
            if not visible and start is None:
                start = i
            elif visible and start is not None:
                if (i - start) / self.fps >= min_seconds:
                    stretches.append((self._time(start), self._time(i)))
                start = None
        return stretches

    def is_live_play(self, time: float) -> bool:
        i = self._index(time)
        return self.bug_visible[i] and self.views[i] in PLAY_VIEWS

    def replays(self, min_seconds: float = 3.0, max_seconds: float = 60.0, lookback: float = 20.0) -> list[Replay]:
        found = []
        for start, end in self.hidden_stretches(min_seconds):
            if end - start > max_seconds:
                continue   # half time, studio or a long graphic, not a replay
            found.append(Replay(start, end, self.last_live_play(start, lookback)))
        return found

    def last_live_play(self, before: float, lookback: float) -> float | None:
        first = self._index(before - lookback)
        for i in range(self._index(before) - 1, first - 1, -1):
            if self.is_live_play(self._time(i)):
                return self._time(i)
        return None

    def is_on_air_play(self, time: float) -> bool:
        """Live broadcast of the match itself: wide shots and close-ups, not replays, bench or crowd."""
        i = self._index(time)
        return self.bug_visible[i] and self.views[i] not in OFF_PLAY_VIEWS

    def first_on_air_play(self, after: float, within: float) -> float | None:
        for i in range(self._index(after), min(self._index(after + within) + 1, len(self.views))):
            if self.is_on_air_play(self._time(i)):
                return self._time(i)
        return None
