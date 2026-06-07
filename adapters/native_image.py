from __future__ import annotations

from typing import Any, Dict
from .base import ImageBackend


class NativeImageBackend(ImageBackend):
    name = "native_image"

    def available(self) -> bool:
        return bool(self.config.get("native_image", {}).get("enabled", False))

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        prompt = request.get("native_prompt") or request.get("prompt") or request.get("positive_prompt")
        return {
            "status": "delegated",
            "backend": self.name,
            "template_id": request.get("template_id"),
            "category": request.get("category"),
            "prompt": prompt,
            "aspect_ratio": request.get("aspect_ratio"),
            "instruction": "Host agent should call its native image generation capability with this prompt.",
        }
