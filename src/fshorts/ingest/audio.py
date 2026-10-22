from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SAMPLE_RATE = 16_000


class AudioExtractor:
    """Writes a mono 16 kHz WAV track, the input format of both audio analysis and Whisper."""

    def __init__(self, binary: str = "ffmpeg") -> None:
        resolved = shutil.which(binary)
        if resolved is None:
            raise RuntimeError(f"'{binary}' not found on PATH")
        self._binary = resolved

    def extract(self, video: Path, target: Path, *, force: bool = False) -> Path:
        if target.is_file() and not force:
            return target
        command = [
            self._binary, "-v", "error", "-y", "-i", str(video),
            "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(target),
        ]
        subprocess.run(command, check=True)
        return target
