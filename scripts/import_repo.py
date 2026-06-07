from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from common import find_root, load_config, resolve_path, write_jsonl

ARG_RE = re.compile(r'\{argument\s+name="([^"]+)"\s+default="([^"]*)"\}', re.I)
PROMPT_HINT_RE = re.compile(r'(prompt|提示词)\s*[:：]', re.I)
REF_WORDS = ["uploaded image", "reference image", "provided image", "portrait photo", "参考图", "上传图片", "原图"]


def clone_or_update(repo_url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (target / ".git").exists():
        subprocess.run(["git", "-C", str(target), "pull", "--ff-only"], check=False)
    elif target.exists():
        raise RuntimeError(f"Target exists but is not a git repo: {target}")
    else:
        subprocess.run(["git", "clone", "--depth=1", repo_url, str(target)], check=True)


def file_category(path: Path) -> str:
    name = path.stem.lower()
    mapping = {
        "ecommerce": "product",
        "ad-creative": "ad",
        "poster": "poster",
        "portrait": "portrait",
        "character": "character",
        "ui": "ui",
        "comparison": "comparison",
    }
    return mapping.get(name, name)


def split_markdown_cases(text: str) -> List[str]:
    # Split on headings. This is intentionally permissive because upstream format may change.
    chunks = re.split(r'\n(?=#{1,4}\s+)', text)
    return [c.strip() for c in chunks if len(c.strip()) > 80]


def extract_prompt(chunk: str) -> str:
    lines = chunk.splitlines()
    for i, line in enumerate(lines):
        if PROMPT_HINT_RE.search(line):
            after = PROMPT_HINT_RE.split(line, maxsplit=1)[-1].strip()
            rest = "\n".join(lines[i + 1:]).strip()
            return (after + "\n" + rest).strip() if after else rest
    # fallback: use chunk text without markdown image links.
    return re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', chunk).strip()


def title_from_chunk(chunk: str, fallback: str) -> str:
    for line in chunk.splitlines():
        m = re.match(r'#{1,4}\s+(.+)', line.strip())
        if m:
            return m.group(1).strip()
    return fallback


def variables(prompt: str) -> Dict[str, str]:
    return {m.group(1): m.group(2) for m in ARG_RE.finditer(prompt)}


def stable_id(source_file: str, title: str, prompt: str) -> str:
    digest = hashlib.sha1((source_file + title + prompt[:300]).encode("utf-8")).hexdigest()[:12]
    return f"import_{digest}"


def parse_markdown(path: Path, repo_root: Path) -> Iterable[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    category = file_category(path)
    for chunk in split_markdown_cases(text):
        title = title_from_chunk(chunk, path.stem)
        prompt = extract_prompt(chunk)
        if len(prompt) < 40:
            continue
        source = str(path.relative_to(repo_root))
        yield {
            "id": stable_id(source, title, prompt),
            "title": title,
            "category": category,
            "source_file": source,
            "original_prompt": prompt,
            "variables": variables(prompt),
            "need_reference_image": any(w.lower() in prompt.lower() for w in REF_WORDS),
            "tags": [category, "imported"],
        }


def parse_json(path: Path, repo_root: Path) -> Iterable[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    rows = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        prompt = item.get("prompt") or item.get("text") or item.get("content") or ""
        if len(prompt) < 40:
            continue
        title = item.get("title") or item.get("name") or path.stem
        source = str(path.relative_to(repo_root))
        out.append({
            "id": stable_id(source, title, prompt),
            "title": title,
            "category": item.get("category") or file_category(path),
            "source_file": source,
            "original_prompt": prompt,
            "variables": variables(prompt),
            "need_reference_image": any(w.lower() in prompt.lower() for w in REF_WORDS),
            "tags": item.get("tags") or ["imported"],
        })
    return out


def import_repo(repo_url: str, local_repo: str | None = None, config_path: str | None = None) -> Path:
    root = find_root(Path(__file__).resolve())
    config = load_config(root, config_path)
    source_dir = resolve_path(root, config.get("paths", {}).get("source_dir"), "./source")
    data_dir = resolve_path(root, config.get("paths", {}).get("data_dir"), "./data")
    target = Path(local_repo).expanduser() if local_repo else source_dir / repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    if not target.exists():
        clone_or_update(repo_url, target)
    repo_root = target.resolve()

    records = []
    for md in list(repo_root.glob("*.md")) + list(repo_root.glob("cases/*.md")):
        records.extend(parse_markdown(md, repo_root))
    for js in repo_root.glob("data/*.json"):
        records.extend(parse_json(js, repo_root))

    # Deduplicate by id.
    uniq = {r["id"]: r for r in records}
    out_path = data_dir / "prompts_raw.jsonl"
    write_jsonl(out_path, uniq.values())
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-url", default="https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts.git")
    parser.add_argument("--local-repo", default=None)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    out = import_repo(args.repo_url, args.local_repo, args.config)
    print(json.dumps({"status": "success", "output": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
