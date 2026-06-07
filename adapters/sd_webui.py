from __future__ import annotations

from typing import Any, Dict
import requests

from .base import ImageBackend


class SDWebUIBackend(ImageBackend):
    name = "sd_webui"

    def _settings(self) -> Dict[str, Any]:
        return self.config.get("sd_webui", {})

    def available(self) -> bool:
        settings = self._settings()
        if not settings.get("enabled", False):
            return False
        api_url = settings.get("api_url", "http://127.0.0.1:7860").rstrip("/")
        try:
            r = requests.get(f"{api_url}/sdapi/v1/progress", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        settings = self._settings()
        api_url = settings.get("api_url", "http://127.0.0.1:7860").rstrip("/")
        payload = {
            "prompt": request.get("positive_prompt") or request.get("prompt"),
            "negative_prompt": request.get("negative_prompt") or "",
            "width": int(request.get("width", 1024)),
            "height": int(request.get("height", 1024)),
            "steps": int(request.get("steps", 28)),
            "cfg_scale": float(request.get("cfg_scale", 7)),
        }
        try:
            r = requests.post(f"{api_url}/sdapi/v1/txt2img", json=payload, timeout=int(settings.get("timeout_seconds", 180)))
            r.raise_for_status()
            return {"status": "success", "backend": self.name, "response": r.json(), "template_id": request.get("template_id")}
        except requests.RequestException as exc:
            return {"status": "error", "backend": self.name, "error": str(exc), "prompt_only_fallback": request}
