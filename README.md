# Universal Image Prompt Skill

A portable, offline-first image prompt skill for agents.

It turns a user's natural-language image request into a high-quality
prompt and routes it to one of several image-generation backends. The
prompt library is **local**; the network is only used at install time.

## Correct backend priority

1. **ComfyUI** — local, first priority. If `comfyui.enabled=true` and
   the server at `comfyui.api_url` is reachable, this is the backend
   that runs. ComfyUI is local, so it works without internet.
2. **native_image** — host agent's built-in image generation
   capability. Used when ComfyUI is not available.
3. **cloud_image** — cloud image model (e.g. OpenAI Images). Only
   considered when both ComfyUI and native_image are unavailable, and
   only when network is up and the API key env var is set. Off by
   default.
4. **sd_webui** — Stable Diffusion WebUI.
5. **prompt_only** — always-available fallback. Returns the final
   prompt and metadata; no image generation call is made.

The order is fixed in `config.example.yaml` under `backend.priority`
and enforced by `scripts/generate.py:select_backend`.

## Why this exists

Many image-prompt collections are written for a specific model or UI.
This skill separates:

1. prompt library data (offline, in `data/`)
2. prompt routing and rewriting (`scripts/router.py`, offline-only)
3. image-generation backend adapters (`adapters/`)

That means the same skill can be used by Hermes, Codex, OpenClaw, a
website workflow, a WeChat article workflow, or any other agent.

## Install

```bash
git clone https://github.com/lqyai2026-droid/image-prompt-skill.git
cd image-prompt-skill
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

## First thing after install: build the local prompt library

```bash
python scripts/bootstrap_prompts.py --online
```

This is the only step that touches the network for prompt data. It
will:

1. Clone the curated upstream prompt repository into `./source/`.
2. Parse markdown / json cases into `data/prompts_raw.jsonl`.
3. Expand raw records into backend-specific fields and write:

       data/prompts_raw.jsonl
       data/prompts_comfy.jsonl
       data/prompts.sqlite

After this completes, **runtime code never searches the network for
prompts**. The router always reads from the local files above.

To refresh the library later, re-run the same command.

If you are already offline, omit `--online` and the script will fall
back to the small `data/seed_prompts.jsonl` shipped in the repo:

```bash
python scripts/bootstrap_prompts.py
```

## Quick start

### 1. `prompt_only` (works on any machine, no ComfyUI required)

```bash
python scripts/generate.py "生成一个黑金风格的 AI 工具站宣传图" --backend prompt_only
```

You will get a JSON object with `status: "prompt_only"` and a
copyable prompt. No image is generated.

### 2. `auto` (use whatever is available)

```bash
python scripts/generate.py "生成一个黑金风格的 AI 工具站宣传图" --backend auto
```

The skill will pick the first available backend in this order:
comfyui → native_image → cloud_image → sd_webui → prompt_only. With
ComfyUI running locally and `comfyui.enabled=true`, you will get
`status: "success"` and a list of output files. With nothing
configured, you will get `status: "prompt_only"`.

### 3. `native_image` (delegate to the host agent's built-in image gen)

```bash
python scripts/generate.py "生成一个高级科技感公众号封面" --backend native_image
```

The result will be `status: "delegated"`. The host agent (Hermes,
OpenClaw, etc.) should call its own image-generation capability with
the returned prompt.

## Configuration

See `config.example.yaml`. The key sections:

```yaml
runtime:
  prompt_source: "local_first"
  allow_network_for_prompt_search: false
  offline_library_required: true

backend:
  mode: "auto"
  priority:
    - "comfyui"
    - "native_image"
    - "cloud_image"
    - "sd_webui"
    - "prompt_only"

comfyui:
  enabled: true
  api_url: "http://127.0.0.1:8188"
  workflow_dir: "./workflows"
  default_workflow: "sdxl_text2image.json"

native_image:
  enabled: true
  provider: "agent_default"

cloud_image:
  enabled: false
  provider: "openai_image"
  api_key_env: "OPENAI_API_KEY"
  model: "gpt-image-1"
  require_network: true

sd_webui:
  enabled: false
  api_url: "http://127.0.0.1:7860"

prompt_only:
  enabled: true
```

`cloud_image` is intentionally off by default. To turn it on, set
`enabled: true` and export the API key in the env var named by
`api_key_env`. The skill never reads or writes the key directly —
the host agent does that.

## Project structure

```text
image-prompt-skill/
├── SKILL.md                  # canonical skill description (OpenClaw reads this)
├── skill.md                  # legacy alias, points to SKILL.md
├── README.md                 # this file
├── config.example.yaml
├── requirements.txt
├── data/
│   ├── seed_prompts.jsonl    # tiny offline fallback library
│   ├── prompts_raw.jsonl     # created by bootstrap --online
│   ├── prompts_comfy.jsonl   # created by bootstrap
│   ├── prompts.sqlite        # created by bootstrap
│   └── README.md
├── adapters/
│   ├── base.py
│   ├── comfyui.py            # first priority, no network scanning
│   ├── native_image.py       # second priority, returns delegated
│   ├── cloud_image.py        # third priority, fallback only
│   ├── sd_webui.py
│   └── prompt_only.py        # always-available final fallback
├── scripts/
│   ├── bootstrap_prompts.py  # install-time, --online is the only network step
│   ├── convert_prompts.py
│   ├── import_repo.py
│   ├── router.py             # OFFLINE-ONLY prompt retrieval
│   ├── generate.py
│   ├── check_capabilities.py
│   └── common.py
├── examples/
│   ├── generate_comfyui.json
│   ├── generate_native_image.json
│   └── prompt_only.json
└── docs/
    ├── OFFLINE_FIRST.md
    ├── BACKEND_PRIORITY.md
    ├── OPENCLAW.md
    ├── AGENT_INTEGRATION.md
    └── DEPLOY.md
```

## Path rules

The skill resolves paths in this order:

1. command-line arguments
2. environment variable `IMAGE_PROMPT_SKILL_HOME`
3. current project directory (where `SKILL.md` and `config.example.yaml` live)
4. relative paths from `config.yaml`

No absolute path is required.

## Documentation

- [docs/OFFLINE_FIRST.md](docs/OFFLINE_FIRST.md) — what "offline first"
  means here, and what it does NOT mean
- [docs/BACKEND_PRIORITY.md](docs/BACKEND_PRIORITY.md) — why ComfyUI is
  first, and how the priority is enforced
- [docs/OPENCLAW.md](docs/OPENCLAW.md) — running this skill under
  OpenClaw
- [docs/AGENT_INTEGRATION.md](docs/AGENT_INTEGRATION.md) — embedding
  this skill in another agent
- [docs/DEPLOY.md](docs/DEPLOY.md) — deployment notes

## License

The skill code is released under MIT. Imported third-party prompt
libraries keep their original licenses. The EvoLinkAI prompt source
is CC0-1.0 at the time this starter was written; verify upstream
license before redistributing imported data.
