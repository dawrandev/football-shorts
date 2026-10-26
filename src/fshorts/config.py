from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ClipConfig:
    pre_seconds: float
    post_seconds: float
    goal_pre_seconds: float
    goal_post_seconds: float
    include_replay: bool
    replay_max_seconds: float
    max_chances: int
    snap_seconds: float


@dataclass(frozen=True)
class OutputConfig:
    width: int
    height: int
    layout: str
    encoder: str
    bitrate: str
    zoom: float = 1.0               # 1.0 = full frame height; larger crops tighter around the action
    top_margin: float = 0.0         # share of frame height at the top kept out of the crop (score bug)
    detect_fps: float = 10.0        # detector rate along a clip; the crop path is interpolated between
    smooth_seconds: float = 0.6
    min_coverage: float = 0.5       # below this share of followed samples a clip falls back to blur
    ball_weights: Path | None = None  # our fine-tuned ball detector; None = pretrained COCO "sports ball"
    window_aspect: float = 0.8      # width/height of the followed window in the "wide" layout (4:5)
    upscaler: str = "lanczos"       # lanczos | realesrgan
    sr_weights: Path | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> OutputConfig:
        paths = {key: Path(raw[key]) if raw.get(key) else None for key in ("ball_weights", "sr_weights")}
        return cls(**{**raw, **paths})


@dataclass(frozen=True)
class AudioPeaksConfig:
    hop_seconds: float
    baseline_seconds: float
    smooth_seconds: float
    min_gap_seconds: float
    min_zscore: float
    min_db_rise: float


@dataclass(frozen=True)
class CommentaryConfig:
    model: str
    compute_type: str
    language: str | None
    phrases: dict[str, float]


@dataclass(frozen=True)
class EventsConfig:
    merge_seconds: float
    max_candidates: int
    audio: AudioPeaksConfig
    commentary: CommentaryConfig

    @classmethod
    def from_dict(cls, raw: dict) -> EventsConfig:
        return cls(
            merge_seconds=raw["merge_seconds"],
            max_candidates=raw["max_candidates"],
            audio=AudioPeaksConfig(**raw["audio"]),
            commentary=CommentaryConfig(**raw["commentary"]),
        )


@dataclass(frozen=True)
class ScoreboardConfig:
    fps: float
    confirmations: int
    min_confidence: float
    region: tuple[int, int, int, int]

    @classmethod
    def from_dict(cls, raw: dict) -> ScoreboardConfig:
        return cls(**{**raw, "region": tuple(raw["region"])})


@dataclass(frozen=True)
class PathsConfig:
    matches: Path
    outputs: Path
    labels: Path


@dataclass(frozen=True)
class AppConfig:
    clip: ClipConfig
    output: OutputConfig
    events: EventsConfig
    scoreboard: ScoreboardConfig
    paths: PathsConfig

    LAYOUTS = ("crop", "wide", "blur")

    @classmethod
    def load(cls, path: Path) -> AppConfig:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = cls(
            clip=ClipConfig(**raw["clip"]),
            output=OutputConfig.from_dict(raw["output"]),
            events=EventsConfig.from_dict(raw["events"]),
            scoreboard=ScoreboardConfig.from_dict(raw["scoreboard"]),
            paths=PathsConfig(**{k: Path(v) for k, v in raw["paths"].items()}),
        )
        config._validate()
        return config

    def _validate(self) -> None:
        if self.clip.pre_seconds < 0 or self.clip.post_seconds < 0:
            raise ValueError("clip window seconds must be non-negative")
        if self.output.layout not in self.LAYOUTS:
            raise ValueError(f"output.layout must be one of {self.LAYOUTS}")
