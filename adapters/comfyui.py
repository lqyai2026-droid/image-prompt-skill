from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .base import ImageBackend


class ComfyUIBackend(ImageBackend):
    name = "comfyui"

    def _settings(self) -> Dict[str, Any]:
        return self.config.get("comfyui", {})

    def available(self) -> bool:
        settings = self._settings()
        if not settings.get("enabled", False):
            return False
        api_url = settings.get("api_url", "http://127.0.0.1:8188").rstrip("/")
        try:
            r = requests.get(f"{api_url}/system_stats", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        settings = self._settings()
        api_url = settings.get("api_url", "http://127.0.0.1:8188").rstrip("/")
        workflow_path = self._resolve_workflow_path(settings)
        if not workflow_path or not workflow_path.exists():
            return {
                "status": "error",
                "backend": self.name,
                "error": "ComfyUI workflow file not found. Configure comfyui.workflow_dir and comfyui.default_workflow.",
                "prompt_only_fallback": request,
            }

        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow = self._patch_workflow(workflow, request)
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        try:
            submit = requests.post(f"{api_url}/prompt", json=payload, timeout=15)
            submit.raise_for_status()
            prompt_id = submit.json().get("prompt_id")
            if not prompt_id:
                return {"status": "error", "backend": self.name, "error": "No prompt_id returned", "response": submit.text}

            timeout = int(settings.get("timeout_seconds", 180))
            started = time.time()
            while time.time() - started < timeout:
                hist = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
                if hist.status_code == 200:
                    data = hist.json()
                    if prompt_id in data:
                        outputs = self._extract_outputs(data[prompt_id])
                        return {
                            "status": "success",
                            "backend": self.name,
                            "prompt_id": prompt_id,
                            "template_id": request.get("template_id"),
                            "category": request.get("category"),
                            "outputs": outputs,
                            "positive_prompt": request.get("positive_prompt"),
                            "negative_prompt": request.get("negative_prompt"),
                        }
                time.sleep(2)
            return {"status": "timeout", "backend": self.name, "prompt_id": prompt_id}
        except requests.RequestException as exc:
            return {"status": "error", "backend": self.name, "error": str(exc), "prompt_only_fallback": request}

    def _resolve_workflow_path(self, settings: Dict[str, Any]) -> Optional[Path]:
        workflow_dir = Path(settings.get("workflow_dir") or self.config.get("paths", {}).get("workflow_dir", "./workflows"))
        if not workflow_dir.is_absolute():
            workflow_dir = self.root_dir / workflow_dir
        default = settings.get("default_workflow")
        if not default:
            return None
        return workflow_dir / default

    def _patch_workflow(self, workflow: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        positive = request.get("positive_prompt") or request.get("prompt") or ""
        negative = request.get("negative_prompt") or ""
        width = int(request.get("width", 1024))
        height = int(request.get("height", 1024))

        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            class_type = str(node.get("class_type", "")).lower()
            title = str(node.get("_meta", {}).get("title", "")).lower()

            # Common ComfyUI nodes: CLIPTextEncode, EmptyLatentImage.
            if "cliptextencode" in class_type:
                if "negative" in title:
                    inputs["text"] = negative
                elif "positive" in title:
                    inputs["text"] = positive
                elif not inputs.get("text"):
                    inputs["text"] = positive
            if "emptylatentimage" in class_type or "latent" in title:
                if "width" in inputs:
                    inputs["width"] = width
                if "height" in inputs:
                    inputs["height"] = height
            if "ksampler" in class_type and "seed" in inputs and request.get("seed"):
                inputs["seed"] = int(request["seed"])
        return workflow

    def _extract_outputs(self, history_item: Dict[str, Any]):
        outputs = []
        for node_output in history_item.get("outputs", {}).values():
            for img in node_output.get("images", []) or []:
                outputs.append(img)
        return outputs
