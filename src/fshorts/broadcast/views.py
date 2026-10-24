from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

# Zero-shot prompts per view; a probe trained on our own labelled frames replaces this later
VIEW_PROMPTS = {
    "wide": ["a wide broadcast camera view of a football pitch with many small players",
             "aerial wide shot of a soccer match"],
    "close": ["a close-up of a football player", "a medium shot of soccer players on the pitch"],
    "crowd": ["football fans in the stadium stands", "a coach and substitutes on the bench"],
    "logo": ["a large tournament logo graphic transition on screen"],
    "goalmouth": ["a goalkeeper diving in front of the goal net", "a view from behind the goal net"],
}


class ViewClassifier(ABC):
    @abstractmethod
    def classify(self, frames: list[np.ndarray]) -> list[str]:
        """One view name per RGB frame."""


class SiglipViewClassifier(ViewClassifier):
    """Zero-shot camera view labels from SigLIP2 image-text similarity."""

    def __init__(self, model_name: str = "google/siglip2-base-patch16-224", device: str = "cuda") -> None:
        import torch
        from transformers import AutoModel, AutoProcessor

        self._torch = torch
        self._device = device
        self._model = AutoModel.from_pretrained(model_name, dtype=torch.float16).to(device).eval()
        self._processor = AutoProcessor.from_pretrained(model_name)
        self._names = list(VIEW_PROMPTS)
        self._groups = [len(VIEW_PROMPTS[n]) for n in self._names]
        texts = [t for n in self._names for t in VIEW_PROMPTS[n]]
        inputs = self._processor(text=texts, return_tensors="pt", padding="max_length", max_length=64)
        with torch.no_grad():
            features = self._model.get_text_features(**{k: v.to(device) for k, v in inputs.items()})
        self._text = self._normalize(features)

    def _normalize(self, features) -> np.ndarray:
        features = getattr(features, "pooler_output", features)
        return self._torch.nn.functional.normalize(features.float(), dim=-1).cpu().numpy()

    def classify(self, frames: list[np.ndarray]) -> list[str]:
        pixels = self._processor(images=frames, return_tensors="pt")["pixel_values"].to(self._device).half()
        with self._torch.no_grad():
            images = self._normalize(self._model.get_image_features(pixel_values=pixels))
        similarity = images @ self._text.T
        bounds = np.cumsum([0] + self._groups)
        per_view = np.stack([similarity[:, a:b].max(axis=1) for a, b in zip(bounds, bounds[1:])], axis=1)
        return [self._names[i] for i in per_view.argmax(axis=1)]
