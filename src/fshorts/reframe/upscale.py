from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

# Upscaled crops look soft; a light unsharp mask restores edges without halos
SHARPEN_AMOUNT = 0.5
SHARPEN_SIGMA = 1.2


class Upscaler(ABC):
    @abstractmethod
    def upscale(self, image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        """RGB image resized to (width, height)."""


class LanczosUpscaler(Upscaler):
    def upscale(self, image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        scaled = cv2.resize(image, size, interpolation=cv2.INTER_LANCZOS4)
        blurred = cv2.GaussianBlur(scaled, (0, 0), SHARPEN_SIGMA)
        return cv2.addWeighted(scaled, 1 + SHARPEN_AMOUNT, blurred, -SHARPEN_AMOUNT, 0)


class RealEsrganUpscaler(Upscaler):
    """Real-ESRGAN general x4 compact model (BSD-3): removes compression blocks and restores edges.

    The source is a ~3.5 Mbit/s YouTube encode, so plain interpolation magnifies its artefacts;
    the network upscales x4 and the result is shrunk to the target size (~16 ms a frame on a 5090).
    """

    def __init__(self, weights: Path, device: str = "cuda") -> None:
        import torch

        self._torch = torch
        self._device = device
        self._model = _compact_generator()
        state = torch.load(weights, map_location="cpu", weights_only=True)
        self._model.load_state_dict(state.get("params", state))
        self._model = self._model.to(device).half().eval()

    def upscale(self, image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        from torch.nn import functional as F

        x = self._torch.from_numpy(np.ascontiguousarray(image)).permute(2, 0, 1)[None].to(self._device).half() / 255
        with self._torch.no_grad():
            # Shrink the x4 result on the GPU: copying a 4K frame back to the CPU costs more than the network
            y = F.interpolate(self._model(x).float(), size=(size[1], size[0]), mode="area")
            return y[0].clamp_(0, 1).mul_(255).byte().permute(1, 2, 0).cpu().numpy()


def _compact_generator(features: int = 64, convs: int = 32, scale: int = 4):
    """SRVGGNetCompact, the architecture of realesr-general-x4v3."""
    from torch import nn
    from torch.nn import functional as F

    class SRVGGNetCompact(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.body = nn.ModuleList([nn.Conv2d(3, features, 3, 1, 1), nn.PReLU(num_parameters=features)])
            for _ in range(convs):
                self.body.extend([nn.Conv2d(features, features, 3, 1, 1), nn.PReLU(num_parameters=features)])
            self.body.append(nn.Conv2d(features, 3 * scale * scale, 3, 1, 1))
            self.upsampler = nn.PixelShuffle(scale)

        def forward(self, x):
            out = x
            for layer in self.body:
                out = layer(out)
            return self.upsampler(out) + F.interpolate(x, scale_factor=scale, mode="nearest")

    return SRVGGNetCompact()
