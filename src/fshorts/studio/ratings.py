from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Reasons a viewer can tick; stored as these keys so the training code does not depend on UI wording
REASONS = (
    "great_moment", "good_cut", "boring", "missed_action", "starts_late", "ends_early", "too_long",
    "ball_lost", "wrong_text", "replay", "bad_quality",
)


@dataclass(frozen=True)
class ShortRating:
    clip_id: str
    stars: int                      # 1-5
    reasons: tuple[str, ...] = ()
    note: str = ""
    start: float = 0.0
    end: float = 0.0
    kind: str = ""
    rated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def __post_init__(self) -> None:
        if not 1 <= self.stars <= 5:
            raise ValueError("stars must be 1-5")
        unknown = set(self.reasons) - set(REASONS)
        if unknown:
            raise ValueError(f"unknown reasons: {sorted(unknown)}")


class RatingStore:
    """Viewer ratings of finished Shorts, one JSON file per match: training data for the ranker."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def load(self, match: str) -> dict[str, ShortRating]:
        path = self._folder / f"{match}.json"
        if not path.is_file():
            return {}
        rows = json.loads(path.read_text(encoding="utf-8"))
        return {r["clip_id"]: ShortRating(**{**r, "reasons": tuple(r["reasons"])}) for r in rows}

    def save(self, match: str, rating: ShortRating) -> None:
        ratings = self.load(match)
        ratings[rating.clip_id] = rating
        self._folder.mkdir(parents=True, exist_ok=True)
        rows = [asdict(r) for r in sorted(ratings.values(), key=lambda r: r.start)]
        (self._folder / f"{match}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
