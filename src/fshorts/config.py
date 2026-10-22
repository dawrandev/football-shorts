from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ClipConfig:
    pre_seconds: float
    post_seconds: float
    include_replay: bool


@dataclass(frozen=True)
class OutputConfig:
    width: int
    height: int
    layout: str
    encoder: str
    bitrate: str


@dataclass(frozen=True)
class PathsConfig:
    matches: Path
    outputs: Path


@dataclass(frozen=True)
class AppConfig:
    clip: ClipConfig
    output: OutputConfig
    paths: PathsConfig

    LAYOUTS = ("crop", "blur")

    @classmethod
    def load(cls, path: Path) -> AppConfig:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = cls(
            clip=ClipConfig(**raw["clip"]),
            output=OutputConfig(**raw["output"]),
            paths=PathsConfig(**{k: Path(v) for k, v in raw["paths"].items()}),
        )
        config._validate()
        return config

    def _validate(self) -> None:
        if self.clip.pre_seconds < 0 or self.clip.post_seconds < 0:
            raise ValueError("clip window seconds must be non-negative")
        if self.output.layout not in self.LAYOUTS:
            raise ValueError(f"output.layout must be one of {self.LAYOUTS}")
