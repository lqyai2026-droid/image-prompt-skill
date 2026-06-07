from __future__ import annotations

from typing import Any, Dict
from .base import ImageBackend


class PromptOnlyBackend(ImageBackend):
    name = "prompt_only"

    def available(self) -> bool:
        return True

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "prompt_only",
            "backend": self.name,
            "template_id": request.get("template_id"),
            "category": request.get("category"),
            "prompt": request.get("native_prompt") or request.get("positive_prompt") or request.get("prompt"),
            "positive_prompt": request.get("positive_prompt"),
            "negative_prompt": request.get("negative_prompt"),
            "recommended_model": request.get("recommended_model"),
            "aspect_ratio": request.get("aspect_ratio"),
        }
