# Universal Image Prompt Skill

A portable, backend-agnostic image prompt skill for agents.

It turns a user's natural-language image request into a high-quality prompt and routes it to one of several backends:

- `native_image`: host agent's built-in image generation capability
- `comfyui`: local or remote ComfyUI API
- `sd_webui`: Stable Diffusion WebUI API
- `prompt_only`: safe fallback that only returns the final prompt

The skill does **not** use absolute paths and does **not** assume ComfyUI exists.

## Why this exists

Many image-prompt collections are written for a specific model or UI. This skill separates:

1. prompt library data
2. prompt routing and rewriting
3. image-generation backend adapters

That means the same skill can be used by Hermes, Codex, OpenClaw, a website workflow, a WeChat article workflow, or any other agent.

## Project structure

```text
image-prompt-skill/
├── skill.md
├── README.md
├── config.example.yaml
├── requirements.txt
├── data/
│   ├── seed_prompts.jsonl
│   └── README.md
├── adapters/
│   ├── base.py
│   ├── comfyui.py
│   ├── native_image.py
│   ├── prompt_only.py
│   └── sd_webui.py
├── scripts/
│   ├── check_capabilities.py
│   ├── convert_prompts.py
│   ├── generate.py
│   ├── import_repo.py
│   └── router.py
├── examples/
│   ├── generate_comfyui.json
│   ├── generate_native_image.json
│   └── prompt_only.json
└── docs/
    ├── DEPLOY.md
    └── AGENT_INTEGRATION.md
```

## Install

```bash
git clone https://github.com/lqyai2026-droid/image-prompt-skill.git
cd image-prompt-skill
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

## Quick start without any image backend

```bash
python scripts/generate.py "生成一个黑金风格的高端 AI 工具站宣传图" --backend prompt_only
```

This works on any computer because `prompt_only` does not need ComfyUI or an image API.

## Use host agent native image generation

```bash
python scripts/generate.py "生成一个高级科技感公众号封面，主题是 AI 改变世界" --backend native_image
```

The result will be `status=delegated`. The host agent should pass the returned prompt to its own image-generation capability.

## Use ComfyUI

Edit `config.yaml`:

```yaml
comfyui:
  enabled: true
  api_url: "http://127.0.0.1:8188"
  workflow_dir: "./workflows"
  default_workflow: "sdxl_text2image.json"
```

Then run:

```bash
python scripts/check_capabilities.py
python scripts/generate.py "生成一个高端男士香水电商广告图，品牌名 AiGold Noir" --backend comfyui
```

## Import external prompt libraries

This repository ships with a small seed library. To import the GPT-Image-2 prompt collection when online:

```bash
python scripts/import_repo.py --repo-url https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts.git
python scripts/convert_prompts.py
```

The converted local data is stored in `data/prompts.sqlite` and can be used offline afterward.

## Path rules

The skill resolves paths in this order:

1. command-line arguments
2. environment variable `IMAGE_PROMPT_SKILL_HOME`
3. current project directory
4. relative paths from `config.yaml`

No absolute path is required.

## License

The skill code is released under MIT. Imported third-party prompt libraries keep their original licenses. The EvoLinkAI prompt source is CC0-1.0 at the time this starter was written; verify upstream license before redistributing imported data.
