from __future__ import annotations

from pathlib import Path


class MatchWorkspace:
    """Per-match folder under outputs that holds every intermediate artifact."""

    def __init__(self, outputs_root: Path, video: Path) -> None:
        self.video = video
        self.root = outputs_root / video.stem
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def audio(self) -> Path:
        return self.root / "audio.wav"

    @property
    def transcript(self) -> Path:
        return self.root / "transcript.json"

    @property
    def candidates(self) -> Path:
        return self.root / "candidates.json"

    @property
    def score_readings(self) -> Path:
        return self.root / "score_readings.json"

    @property
    def goals(self) -> Path:
        return self.root / "goals.json"
