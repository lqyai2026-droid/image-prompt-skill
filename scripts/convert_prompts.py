from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from common import ensure_db, find_root, iter_jsonl, load_config, resolve_path, write_jsonl


def infer_model(category: str, text: str) -> str:
    t = (category + " " + text).lower()
    if any(w in t for w in ["anime", "二次元", "动漫"]):
        return "animagine_xl"
    if any(w in t for w in ["poster", "海报", "ui", "interface", "technology", "科技"]):
        return "flux"
    return "juggernaut_xl"


def workflow_profile(category: str) -> str:
    return {
        "product": "product_ad",
        "ecommerce": "product_ad",
        "poster": "tech_poster",
        "social_cover": "social_cover",
        "anime": "anime_character",
        "character": "character_design",
        "portrait": "portrait",
        "ui": "ui_mockup",
        "ad": "ad_creative",
    }.get(category, "text2image")


def default_aspect(category: str) -> str:
    return {
        "product": "1:1",
        "ecommerce": "1:1",
        "poster": "16:9",
        "social_cover": "16:9",
        "anime": "2:3",
        "character": "2:3",
        "portrait": "3:4",
        "ui": "16:9",
    }.get(category, "1:1")


def convert_one(row: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    original = row.get("original_prompt") or ""
    category = row.get("category") or "general"
    negative = config.get("prompt", {}).get("negative_prompt", "low quality, blurry, watermark")
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "category": category,
        "tags": row.get("tags") or [category],
        "original_prompt": original,
        "comfy_positive": f"{original}\n\nStyle translation for SDXL/Flux: high quality, professional composition, detailed lighting, clean subject separation, coherent scene, sharp focus",
        "comfy_negative": negative,
        "native_prompt": f"Create an image based on this production prompt. Preserve the intent, composition, subject, style, and constraints.\n\n{original}",
        "recommended_model": infer_model(category, original),
        "workflow_profile": workflow_profile(category),
        "aspect_ratio": default_aspect(category),
        "need_reference_image": bool(row.get("need_reference_image")),
        "variables": row.get("variables") or {},
    }


def convert(config_path: str | None = None) -> Dict[str, str]:
    root = find_root(Path(__file__).resolve())
    config = load_config(root, config_path)
    data_dir = resolve_path(root, config.get("paths", {}).get("data_dir"), "./data")
    raw_path = data_dir / "prompts_raw.jsonl"
    seed_path = data_dir / "seed_prompts.jsonl"
    rows = list(iter_jsonl(raw_path)) if raw_path.exists() else list(iter_jsonl(seed_path))
    converted = [convert_one(r, config) if "native_prompt" not in r else r for r in rows]

    comfy_path = data_dir / "prompts_comfy.jsonl"
    write_jsonl(comfy_path, converted)

    db_path = data_dir / "prompts.sqlite"
    conn = ensure_db(db_path)
    for r in converted:
        conn.execute(
            """
            INSERT OR REPLACE INTO prompts
            (id,title,category,tags,original_prompt,comfy_positive,comfy_negative,native_prompt,recommended_model,workflow_profile,aspect_ratio,need_reference_image)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                r.get("id"), r.get("title"), r.get("category"), json.dumps(r.get("tags", []), ensure_ascii=False),
                r.get("original_prompt"), r.get("comfy_positive"), r.get("comfy_negative"), r.get("native_prompt"),
                r.get("recommended_model"), r.get("workflow_profile"), r.get("aspect_ratio"), int(bool(r.get("need_reference_image"))),
            ),
        )
    conn.commit()
    conn.close()
    return {"jsonl": str(comfy_path), "sqlite": str(db_path), "count": str(len(converted))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    print(json.dumps({"status": "success", **convert(args.config)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
