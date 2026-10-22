from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    """A moment in the video (seconds from file start) that may be worth a clip."""

    time: float
    score: float
    sources: tuple[str, ...]
    details: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict:
        data = asdict(self)
        data["sources"] = list(self.sources)
        data["details"] = list(self.details)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Candidate:
        return cls(
            time=data["time"],
            score=data["score"],
            sources=tuple(data["sources"]),
            details=tuple(data.get("details", ())),
        )


class EventSource(ABC):
    """One independent signal that proposes candidate moments from the match audio."""

    name: str

    @abstractmethod
    def detect(self, audio: Path) -> list[Candidate]:
        ...
