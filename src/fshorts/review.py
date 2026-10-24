from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

REASONS = {
    "g": "goal",
    "c": "chance",
    "s": "save",
    "a": "attack",
    "b": "boring",
    "x": "bad_cut",
    "r": "replay_only",
    "m": "missed_action",   # the right moment, but the window misses the key action
    "j": "junk_frames",     # an unrelated shot or replay tail at an edge
    "k": "skill",           # player skill highlight rather than a chance
}


@dataclass(frozen=True)
class ClipLabel:
    clip_id: str
    kind: str
    start: float
    end: float
    accepted: bool
    reason: str
    labelled_at: str
    note: str = ""


class LabelStore:
    """Human accept/reject labels per match: the training data of the future highlight model."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, ClipLabel]:
        if not self._path.is_file():
            return {}
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return {item["clip_id"]: ClipLabel(**item) for item in raw}

    def save(self, label: ClipLabel) -> None:
        labels = self.load()
        labels[label.clip_id] = label
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(l) for l in labels.values()], ensure_ascii=False, indent=1), encoding="utf-8"
        )


def open_in_player(path: Path) -> None:
    os.startfile(path)  # Windows default video player


class ReviewSession:
    """Walks through unlabelled clips; answer y/n, then a reason letter."""

    def __init__(
        self,
        store: LabelStore,
        ask: Callable[[str], str] = input,
        show: Callable[[Path], None] = open_in_player,
    ) -> None:
        self._store = store
        self._ask = ask
        self._show = show

    def run(self, clips: list[dict], clips_dir: Path) -> int:
        done = self._store.load()
        pending = [c for c in clips if c["id"] not in done]
        legend = " ".join(f"{k}={v}" for k, v in REASONS.items())
        for number, clip in enumerate(pending, 1):
            self._show(clips_dir / clip["file"])
            answer = self._ask(
                f"[{number}/{len(pending)}] {clip['kind']} {clip['label']} ({clip['end'] - clip['start']:.0f}s)"
                f"  keep? y/n, q=quit: "
            ).strip().lower()
            if answer == "q":
                return number - 1
            if answer not in ("y", "n"):
                continue
            reason = REASONS.get(self._ask(f"  reason ({legend}): ").strip().lower(), "unspecified")
            self._store.save(ClipLabel(
                clip_id=clip["id"], kind=clip["kind"], start=clip["start"], end=clip["end"],
                accepted=answer == "y", reason=reason,
                labelled_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ))
        return len(pending)
