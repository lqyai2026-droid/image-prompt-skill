from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("IMAGE_PROMPT_SKILL_HOME")
    if env:
        return Path(env).expanduser().resolve()
    p = (start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "skill.md").exists() and (candidate / "config.example.yaml").exists():
            return candidate
    return p


def load_config(root: Path, config_path: str | None = None) -> Dict[str, Any]:
    path = Path(config_path).expanduser() if config_path else root / "config.yaml"
    if not path.exists():
        path = root / "config.example.yaml"
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def resolve_path(root: Path, value: str | None, default: str) -> Path:
    path = Path(value or default).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            tags TEXT,
            original_prompt TEXT,
            comfy_positive TEXT,
            comfy_negative TEXT,
            native_prompt TEXT,
            recommended_model TEXT,
            workflow_profile TEXT,
            aspect_ratio TEXT,
            need_reference_image INTEGER
        )
        """
    )
    conn.commit()
    return conn


def aspect_to_size(aspect_ratio: str) -> Tuple[int, int]:
    mapping = {
        "1:1": (1024, 1024),
        "16:9": (1344, 768),
        "9:16": (768, 1344),
        "3:2": (1216, 832),
        "2:3": (832, 1216),
        "4:3": (1152, 864),
        "3:4": (864, 1152),
    }
    return mapping.get(aspect_ratio, (1024, 1024))
