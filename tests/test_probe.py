from pathlib import Path

import pytest

from fshorts.cli import main
from fshorts.ingest import FfprobeProber, ProbeError


def test_probe_reads_metadata(sample_video):
    info = FfprobeProber().probe(sample_video)

    assert (info.width, info.height) == (1280, 720)
    assert info.fps == pytest.approx(25.0)
    assert info.duration_seconds == pytest.approx(3.0, abs=0.1)
    assert info.video_codec == "h264"
    assert info.has_audio
    assert info.duration_label == "00:00:03"


def test_probe_missing_file_raises(tmp_path):
    with pytest.raises(ProbeError, match="file not found"):
        FfprobeProber().probe(tmp_path / "nope.mp4")


def test_probe_non_video_raises(tmp_path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a video")

    with pytest.raises(ProbeError):
        FfprobeProber().probe(text_file)


def test_cli_probe_prints_summary(sample_video, capsys):
    assert main(["probe", str(sample_video)]) == 0
    assert "1280x720" in capsys.readouterr().out


def test_cli_probe_error_exit_code(tmp_path, capsys):
    assert main(["probe", str(Path(tmp_path) / "nope.mp4")]) == 1
    assert "error:" in capsys.readouterr().err
