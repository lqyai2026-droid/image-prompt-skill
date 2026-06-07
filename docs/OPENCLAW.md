# OPENCLAW.md

## Running this skill under OpenClaw

OpenClaw discovers skills by reading `SKILL.md` (uppercase) at the
root of each skill directory. This repo ships an uppercase
`SKILL.md` precisely for that reason. The legacy lowercase
`skill.md` is kept as a deprecation shim for older loaders.

## Setup

1. **Place the repo under a path OpenClaw scans.**

   The exact path depends on the OpenClaw deployment, but a typical
   layout is:

   ```
   <openclaw-skills-root>/
   └── image-prompt-skill/
       ├── SKILL.md
       ├── config.example.yaml
       ├── data/
       ├── adapters/
       └── scripts/
   ```

2. **Install dependencies inside the skill's own venv** (if OpenClaw
   runs skills in a sandboxed venv):

   ```bash
   cd <openclaw-skills-root>/image-prompt-skill
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Build the local prompt library once, while online.**

   ```bash
   python scripts/bootstrap_prompts.py --online
   ```

   After this, the local files
   `data/prompts.sqlite`, `data/prompts_comfy.jsonl`, and
   `data/prompts_raw.jsonl` exist. The skill is now self-contained
   for prompt retrieval.

4. **Configure the backend you want.**

   Copy `config.example.yaml` to `config.yaml` and adjust:

   - `comfyui.api_url` to match your local ComfyUI (default
     `http://127.0.0.1:8188`).
   - `comfyui.enabled: true` if you want ComfyUI to be the default
     first-priority backend.
   - `cloud_image.enabled: true` and a real `api_key_env` if you
     want the cloud fallback available.

## How OpenClaw invokes the skill

OpenClaw typically calls a skill by name with a natural-language
intent. This skill exposes a single CLI entry point:

```bash
python scripts/generate.py "<user intent>" --backend auto
```

OpenClaw should:

- Pipe stdout (a JSON object) back to its own user-visible output.
- Treat `status: "delegated"` (from `native_image` or `cloud_image`)
  as a signal to call its own image-generation facility with the
  prompt that the skill returned, then store / surface the result.
- Treat `status: "prompt_only"` as a graceful fallback: surface the
  final prompt to the user as a copyable text block.
- Treat `status: "success"` (from ComfyUI / SD WebUI) as a real
  generated image; the JSON contains output file references.

## What OpenClaw should NOT do

- **Do not have the skill fetch prompts from the network at
  runtime.** The whole point of the local library is that prompt
  retrieval is offline-only. If you find yourself wanting to make
  router.py call the network, you are undoing this skill's central
  guarantee. Re-run `bootstrap_prompts.py --online` instead and
  refresh the library.

- **Do not silently swap backends.** If the user asked for ComfyUI
  and ComfyUI is not running, the skill returns `prompt_only`. That
  is intentional. Re-routing to a cloud model without telling the
  user would spend their API budget on a request they did not make.

- **Do not read the cloud_image API key from this skill.** This
  skill never holds the key. OpenClaw / the host agent reads the
  env var named in `cloud_image.api_key_env` at call time.

## Example invocation from an OpenClaw tool

A tool-style wrapper for OpenClaw could look like:

```python
import json
import subprocess

def run_image_skill(intent: str, backend: str = "auto", aspect_ratio: str | None = None) -> dict:
    cmd = ["python", "scripts/generate.py", intent, "--backend", backend]
    if aspect_ratio:
        cmd += ["--aspect-ratio", aspect_ratio]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    if payload.get("status") == "delegated":
        # OpenClaw fulfills the delegated call against its own image backend
        ...
    return payload
```

The exact glue depends on the OpenClaw version, but the rule is
constant: trust the skill's output shape, do not bypass it.

## Re-running the bootstrap step

To update the local library with a newer upstream:

```bash
python scripts/bootstrap_prompts.py --online
```

This is safe to run any time. The script is idempotent: it
overwrites `data/prompts_raw.jsonl` with the freshly parsed upstream
records and rebuilds `data/prompts_comfy.jsonl` and
`data/prompts.sqlite`.
