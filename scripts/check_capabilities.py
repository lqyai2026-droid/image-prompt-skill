from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import find_root, load_config
from adapters import ComfyUIBackend, NativeImageBackend, PromptOnlyBackend, SDWebUIBackend


def check(config_path: str | None = None):
    root = find_root(Path(__file__).resolve())
    config = load_config(root, config_path)
    backends = [
        NativeImageBackend(config, root),
        ComfyUIBackend(config, root),
        SDWebUIBackend(config, root),
        PromptOnlyBackend(config, root),
    ]
    return {b.name: b.available() for b in backends}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    print(json.dumps(check(args.config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
