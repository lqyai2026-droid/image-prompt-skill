"""
Prompt router.

This module is OFFLINE ONLY.  It must never make a network call.

    Why: runtime prompt retrieval must be deterministic and independent
    of network availability.  If router.py went online, then a flaky
    Wi-Fi would change the prompt your backend receives.

    The only place this skill is allowed to fetch prompts from the
    network is scripts/bootstrap_prompts.py (the install / update step).

Local retrieval order (do not change without updating the docs):

    1. data/prompts.sqlite
    2. data/prompts_comfy.jsonl
    3. data/seed_prompts.jsonl
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from common import aspect_to_size, find_root, iter_jsonl, load_config, resolve_path

CATEGORY_KEYWORDS = {
    "product": ["产品", "商品", "电商", "主图", "香水", "护肤", "包装", "广告图"],
    "poster": ["海报", "宣传图", "科技", "网站", "hero", "banner", "黑金", "AI"],
    "social_cover": ["公众号", "封面", "小红书", "抖音封面", "文章", "缩略图"],
    "anime": ["二次元", "动漫", "anime", "角色", "老婆"],
    "portrait": ["人像", "写真", "肖像", "头像"],
    "ui": ["UI", "界面", "app", "网页", "dashboard", "mockup"],
    "ad": ["广告", "营销", "品牌", "campaign", "创意"],
}


def infer_category(intent: str) -> str:
    text = intent.lower()
    scores = {}
    for cat, words in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for w in words if w.lower() in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "poster"


def infer_aspect_ratio(intent: str, category: str, override: str | None = None) -> str:
    if override:
        return override
    lower = intent.lower()
    if "9:16" in lower or "抖音" in lower or "竖版" in lower:
        return "9:16"
    if "16:9" in lower or "网站" in lower or "banner" in lower or "hero" in lower:
        return "16:9"
    if "公众号" in lower or "封面" in lower:
        return "16:9"
    if category == "product":
        return "1:1"
    if category == "anime":
        return "2:3"
    return "1:1"


def score_record(intent: str, category: str, rec: Dict[str, Any]) -> int:
    hay = " ".join(str(rec.get(k, "")) for k in ["title", "category", "tags", "original_prompt", "comfy_positive", "native_prompt"]).lower()
    score = 0
    if rec.get("category") == category:
        score += 8
    for token in set(intent.lower().replace("，", " ").replace(",", " ").split()):
        if token and token in hay:
            score += 2
    for word in CATEGORY_KEYWORDS.get(category, []):
        if word.lower() in intent.lower() and word.lower() in hay:
            score += 3
    return score


def load_records(root: Path, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    data_dir = resolve_path(root, config.get("paths", {}).get("data_dir"), "./data")
    db_path = data_dir / "prompts.sqlite"
    records: List[Dict[str, Any]] = []
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT * FROM prompts"):
            records.append(dict(row))
        conn.close()
    if not records:
        for path in [data_dir / "prompts_comfy.jsonl", data_dir / "seed_prompts.jsonl"]:
            if path.exists():
                records.extend(iter_jsonl(path))
    return records


def route(intent: str, backend: str = "auto", aspect_ratio: str | None = None, config_path: str | None = None) -> Dict[str, Any]:
    root = find_root(Path(__file__).resolve())
    config = load_config(root, config_path)
    category = infer_category(intent)
    aspect = infer_aspect_ratio(intent, category, aspect_ratio)
    records = load_records(root, config)
    if not records:
        raise RuntimeError("No prompt records found. Run scripts/convert_prompts.py or keep data/seed_prompts.jsonl.")
    chosen = max(records, key=lambda r: score_record(intent, category, r))
    width, height = aspect_to_size(aspect)
    negative = chosen.get("comfy_negative") or config.get("prompt", {}).get("negative_prompt", "low quality, blurry, watermark")

    native_prompt = chosen.get("native_prompt") or chosen.get("original_prompt") or chosen.get("comfy_positive")
    positive = chosen.get("comfy_positive") or native_prompt

    # Lightweight intent fusion: keep template style but include user's concrete request.
    fused_native = f"{native_prompt}\n\nUser request to satisfy: {intent}"
    fused_positive = f"{positive}, {intent}, high quality, professional composition"

    return {
        "template_id": chosen.get("id"),
        "title": chosen.get("title"),
        "category": chosen.get("category") or category,
        "matched_category": category,
        "backend": backend,
        "positive_prompt": fused_positive,
        "negative_prompt": negative,
        "native_prompt": fused_native,
        "recommended_model": chosen.get("recommended_model"),
        "workflow_profile": chosen.get("workflow_profile"),
        "aspect_ratio": aspect,
        "width": width,
        "height": height,
        "need_reference_image": bool(chosen.get("need_reference_image")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("intent")
    parser.add_argument("--backend", default="auto")
    parser.add_argument("--aspect-ratio", default=None)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    print(json.dumps(route(args.intent, args.backend, args.aspect_ratio, args.config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
