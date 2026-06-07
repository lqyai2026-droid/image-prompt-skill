"""
bootstrap_prompts.py
====================

ONE-SHOT, INSTALL-TIME STEP.

This is the ONLY script in this skill that is allowed to touch the
network for prompt data.  It is intended to be run:

    python scripts/bootstrap_prompts.py --online

...right after cloning the repo, so that the local prompt library
(data/prompts.sqlite, data/prompts_comfy.jsonl, data/prompts_raw.jsonl)
is fully populated.  After this, runtime code (router.py, generate.py,
all adapters) operates entirely offline against the local library.

What it does:

    1. (--online only) Clones / pulls a curated upstream prompt
       repository into ./source/, then parses every markdown / json
       case into data/prompts_raw.jsonl.

    2. Runs convert_prompts.py to expand raw records into
       backend-specific fields and persist them to:

            data/prompts_comfy.jsonl
            data/prompts.sqlite

    3. If --online is NOT given, it falls back to data/seed_prompts.jsonl
       (a tiny, license-clean library shipped in the repo) so the skill
       is usable on a freshly cloned offline machine.

Usage:

    # Online, full library:
    python scripts/bootstrap_prompts.py --online

    # Online, custom upstream:
    python scripts/bootstrap_prompts.py --online \\
        --repo-url https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts.git

    # Offline (uses shipped seed library only):
    python scripts/bootstrap_prompts.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import find_root, load_config, resolve_path  # noqa: E402

# import_repo and convert_prompts are imported lazily so the offline
# path (--online not given) does not require git to be installed.
import convert_prompts  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--online",
        action="store_true",
        help="Fetch the upstream prompt library from git. Required at install time.",
    )
    parser.add_argument(
        "--repo-url",
        default="https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts.git",
        help="Upstream prompt repository to clone (used with --online).",
    )
    parser.add_argument("--local-repo", default=None)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    root = find_root(Path(__file__).resolve())
    config = load_config(root, args.config)

    if args.online:
        # Lazy import: keeps git optional for the offline path.
        import import_repo
        raw = import_repo.import_repo(args.repo_url, args.local_repo, args.config)
        print(json.dumps(
            {"status": "success", "stage": "import", "raw": str(raw)},
            ensure_ascii=False, indent=2,
        ))

    converted = convert_prompts.convert(args.config)
    print(json.dumps(
        {"status": "success", "stage": "convert", **converted},
        ensure_ascii=False, indent=2,
    ))

    data_dir = resolve_path(root, config.get("paths", {}).get("data_dir"), "./data")
    print(json.dumps(
        {
            "status": "success",
            "library_files": {
                "raw": str(data_dir / "prompts_raw.jsonl"),
                "comfy": str(data_dir / "prompts_comfy.jsonl"),
                "sqlite": str(data_dir / "prompts.sqlite"),
            },
            "message": (
                "Local prompt library is ready. Runtime code is now offline-only. "
                "Re-run with --online to refresh the library."
            ),
        },
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
