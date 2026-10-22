from pathlib import Path

import pytest

from fshorts.config import AppConfig

ROOT = Path(__file__).resolve().parents[1]


def test_repo_config_loads():
    config = AppConfig.load(ROOT / "config.yaml")

    assert config.output.width == 1080
    assert config.output.height == 1920
    assert config.output.layout in AppConfig.LAYOUTS
    assert config.paths.matches == Path("data/matches")


def test_invalid_layout_rejected(tmp_path):
    text = (ROOT / "config.yaml").read_text(encoding="utf-8")
    bad = tmp_path / "config.yaml"
    bad.write_text(text.replace("layout: crop", "layout: square"), encoding="utf-8")

    with pytest.raises(ValueError, match="layout"):
        AppConfig.load(bad)
