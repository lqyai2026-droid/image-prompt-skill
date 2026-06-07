"""
Cloud image backend.

This backend is a FALLBACK ONLY:
    comfyui  -> first priority (local)
    native_image -> host agent's built-in image capability
    cloud_image  -> here, only when neither of the above is available
    sd_webui
    prompt_only  -> last resort

Rules:
    - Never enabled by default. Must be turned on explicitly in config.
    - API key is read from environment variable only. Never hard-coded.
    - If network is unavailable, available() returns False.
    - If the configured API key env var is missing, available() returns False.
    - generate() may either:
        (a) call the cloud image API directly when the host agent trusts
            this skill to make outbound HTTPS calls, OR
        (b) return a "delegated" payload so the host agent itself performs
            the call.  We default to (b) for safety; the skill does not
        silently make network calls during normal image generation.
"""
from __future__ import annotations

import os
import socket
from typing import Any, Dict


from .base import ImageBackend


def _has_network() -> bool:
    """
    Cheap, dependency-free network probe.
    We do NOT actually contact any external host here (that would be a
    network call from inside a function whose job is to decide whether
    to make a network call).  We just check that DNS is reachable.
    """
    try:
        socket.getaddrinfo("api.openai.com", 443)
        return True
    except (socket.gaierror, OSError):
        return False


class CloudImageBackend(ImageBackend):
    name = "cloud_image"

    def _settings(self) -> Dict[str, Any]:
        return self.config.get("cloud_image", {})

    def available(self) -> bool:
        settings = self._settings()
        if not settings.get("enabled", False):
            return False
        if settings.get("require_network", True) and not _has_network():
            return False
        key_env = settings.get("api_key_env", "OPENAI_API_KEY")
        if not os.environ.get(key_env):
            return False
        return True

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a 'delegated' payload.  The host agent (Hermes / OpenClaw /
        a custom orchestrator) sees this payload, reads the API key from
        its own secret store, performs the actual HTTP call, and stores
        the result.  The skill itself never embeds API keys and never
        hard-codes provider URLs.
        """
        settings = self._settings()
        return {
            "status": "delegated",
            "backend": self.name,
            "template_id": request.get("template_id"),
            "category": request.get("category"),
            "aspect_ratio": request.get("aspect_ratio"),
            "prompt": request.get("positive_prompt") or request.get("prompt"),
            "provider": settings.get("provider", "openai_image"),
            "model": settings.get("model", "gpt-image-1"),
            "api_key_env": settings.get("api_key_env", "OPENAI_API_KEY"),
            "width": request.get("width"),
            "height": request.get("height"),
            "instruction": (
                "Host agent should read the API key from the named env var, "
                "call the cloud image provider with these parameters, and "
                "store the returned image. Do not echo the API key in any log."
            ),
        }
