from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow direct script execution without installing as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import ComfyUIBackend, NativeImageBackend, PromptOnlyBackend, SDWebUIBackend
from common import find_root, load_config
from router import route


def select_backend(name: str, config, root):
    registry = {
        "native_image": NativeImageBackend(config, root),
        "comfyui": ComfyUIBackend(config, root),
        "sd_webui": SDWebUIBackend(config, root),
        "prompt_only": PromptOnlyBackend(config, root),
    }
    if name != "auto":
        backend = registry.get(name)
        if not backend:
            raise ValueError(f"Unknown backend: {name}")
        if backend.available() or name == "prompt_only":
            return backend
        return registry["prompt_only"]

    for candidate in config.get("backend", {}).get("priority", ["native_image", "comfyui", "sd_webui", "prompt_only"]):
        backend = registry.get(candidate)
        if backend and backend.available():
            return backend
    return registry["prompt_only"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("intent")
    parser.add_argument("--backend", default="auto")
    parser.add_argument("--aspect-ratio", default=None)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    root = find_root(Path(__file__).resolve())
    config = load_config(root, args.config)
    request = route(args.intent, args.backend, args.aspect_ratio, args.config)
    backend = select_backend(args.backend, config, root)
    result = backend.generate(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
