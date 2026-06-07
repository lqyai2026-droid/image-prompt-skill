from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow direct script execution without installing as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import (
    CloudImageBackend,
    ComfyUIBackend,
    NativeImageBackend,
    PromptOnlyBackend,
    SDWebUIBackend,
)
from common import find_root, load_config
from router import route


# Fixed priority used when config does not specify its own list, or when
# the configured list is missing items.  ComfyUI is FIRST.
DEFAULT_PRIORITY = [
    "comfyui",
    "native_image",
    "cloud_image",
    "sd_webui",
    "prompt_only",
]


def _build_registry(config, root):
    """
    Build a name -> backend instance registry.  Order is irrelevant; we
    pick the right one in select_backend().
    """
    return {
        "comfyui": ComfyUIBackend(config, root),
        "native_image": NativeImageBackend(config, root),
        "cloud_image": CloudImageBackend(config, root),
        "sd_webui": SDWebUIBackend(config, root),
        "prompt_only": PromptOnlyBackend(config, root),
    }


def select_backend(name: str, config, root):
    """
    Backend selection policy.

    1) If the user explicitly named a backend:
        - comfyui      -> try it; if it reports not available, fall back to prompt_only.
                          (We never silently substitute another backend when the user
                          asked for comfyui, because that would hide a config bug.)
        - native_image -> always returns a "delegated" payload.  Always usable.
        - cloud_image  -> require both cloud_image.enabled=true AND network AND api key.
                          If not, fall back to prompt_only.
        - sd_webui     -> try it; if not available, fall back to prompt_only.
        - prompt_only  -> always usable, always selected.

    2) If backend="auto" (or anything we don't recognize), walk the
       priority list in config.yaml and pick the first one that reports
       available() == True.  prompt_only is always available, so we
       always return something.

    Prompt retrieval never depends on network access: it is done by
    router.route() above, which reads only local files.  The network is
    only touched by:
        - cloud_image.generate() (when delegated or direct call happens)
        - bootstrap_prompts.py   (install / update step, not at run time)
    """
    registry = _build_registry(config, root)
    prompt_only = registry["prompt_only"]

    if name and name != "auto":
        backend = registry.get(name)
        if backend is None:
            return prompt_only  # unknown name -> safe fallback

        # explicit user request: try it, but degrade to prompt_only on hard
        # unavailability so the user is not given a misleading error.
        if name == "prompt_only":
            return backend
        if name == "native_image":
            return backend  # always usable; generate() returns delegated
        if backend.available():
            return backend
        return prompt_only

    # auto mode
    priority = config.get("backend", {}).get("priority") or DEFAULT_PRIORITY
    for candidate in priority:
        backend = registry.get(candidate)
        if backend and backend.available():
            return backend
    return prompt_only


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
