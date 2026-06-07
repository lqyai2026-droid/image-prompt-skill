# BACKEND_PRIORITY.md

## The priority list, and why

The backend priority is fixed in `config.example.yaml`:

```yaml
backend:
  mode: "auto"
  priority:
    - "comfyui"
    - "native_image"
    - "cloud_image"
    - "sd_webui"
    - "prompt_only"
```

It is enforced in `scripts/generate.py:select_backend`. Each backend
implements an `available()` method that returns a boolean; the first
backend whose `available()` is `True` is selected. `prompt_only` is
always available, so something always runs.

## Why ComfyUI is first

- **Cost.** If the user is already running a local ComfyUI, they paid
  for the GPU. The skill should use it, not pay again for a cloud
  model.
- **Latency.** A localhost HTTP call is sub-millisecond, and ComfyUI
  is a single tool that already handles model selection, sampler
  settings, and workflow orchestration. Going through a cloud model
  adds network latency and round-trips through the provider.
- **Quality control.** ComfyUI workflows give the user full control
  over the generation. A native image model or a cloud model gives
  the user whatever the vendor ships. For a power user with a
  ComfyUI workflow directory, ComfyUI is the better default.
- **Offline.** As `OFFLINE_FIRST.md` explains, a configured ComfyUI
  works without internet. Cloud models do not.

## Why native_image is second

When the user does not have ComfyUI, the next thing to try is the
host agent's own image-generation capability. The reasons are
similar to ComfyUI's:

- **Cost.** The host agent may already have a budget for image
  generation. Using it first is cheaper than going to the cloud.
- **Latency.** Native generation is usually faster than a cloud
  round-trip.
- **Reliability.** A native capability is, by definition, present in
  the runtime that is already calling this skill. A cloud call is
  one more external dependency that can fail.

This skill does not pretend to call the host's image capability
itself. The `native_image` adapter's `generate()` returns a
`delegated` payload; the host agent sees that payload and performs
the actual call.

## Why cloud_image is third

Cloud image models are last-resort backends for users who:

- Do not have ComfyUI,
- Are running on a host agent that has no native image capability,
- Have network access, and
- Have an API key.

This is a narrow set of users, which is why `cloud_image` is off by
default. The skill never stores the API key itself — the host agent
reads the env var named in `cloud_image.api_key_env` at the moment
of the call.

If `cloud_image` is not available (turned off, no network, no key),
`available()` returns `False` and the priority list moves on.

## Why sd_webui is fourth

Stable Diffusion WebUI is supported for users who run that
particular UI. It is placed after ComfyUI and after the
host-agent's native capability because SD WebUI:

- Is local but historically less workflow-driven than ComfyUI,
- Is less commonly deployed in agent runtimes than ComfyUI is today,
- And is included mostly for parity with the original "portable
  image prompt skill" that this repo forked from.

## Why prompt_only is last

`prompt_only` is not a backend that generates images. It is a safe
fallback that returns the constructed prompt and metadata. The skill
uses it when:

- The user explicitly asked for it (`--backend prompt_only`), or
- No other backend is available.

It is critical that `prompt_only.available()` is hard-coded to
`True`. Without this guarantee, the skill could be in a state where
no backend is selected and an unhandled error escapes.

## How the user can override the order

The user can force a specific backend with `--backend NAME`:

```bash
python scripts/generate.py "..." --backend comfyui
python scripts/generate.py "..." --backend native_image
python scripts/generate.py "..." --backend cloud_image
python scripts/generate.py "..." --backend sd_webui
python scripts/generate.py "..." --backend prompt_only
```

When the user names a backend, `select_backend` tries it. If it is
unavailable, the skill falls back to `prompt_only`. It does **not**
silently substitute a different backend. This is intentional: a
silent substitution would mask a configuration mistake, and the user
is better off seeing a `prompt_only` result with the final prompt
than getting an image from a backend they did not ask for.

## Implementation pointers

- Priority list and selection logic:
  `scripts/generate.py:select_backend`
- Per-backend availability:
  - `adapters/comfyui.py:available` — checks `comfyui.enabled` and
    pings `{api_url}/system_stats`.
  - `adapters/native_image.py:available` — always `True` (delegation
    is always possible).
  - `adapters/cloud_image.py:available` — checks `cloud_image.enabled`,
    DNS resolvability, and the API key env var.
  - `adapters/sd_webui.py:available` — checks `sd_webui.enabled` and
    pings `{api_url}/sdapi/v1/progress`.
  - `adapters/prompt_only.py:available` — always `True`.
