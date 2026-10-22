from __future__ import annotations

import os
import sys
from pathlib import Path


def register_cuda12_dlls() -> None:
    """Expose pip-installed CUDA 12 cuBLAS/cuDNN DLLs to ctranslate2.

    The venv's PyTorch ships CUDA 13, but ctranslate2 (faster-whisper) is built
    against CUDA 12 and loads its DLLs through PATH on Windows.
    """
    if sys.platform != "win32":
        return
    try:
        import nvidia
    except ImportError:
        return
    for root in map(Path, nvidia.__path__):
        for bin_dir in root.glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
