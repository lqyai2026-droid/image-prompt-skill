# OFFLINE_FIRST.md

## What "offline first" means in this skill

In this skill, **offline-first** refers specifically to the **prompt
library**, not to the image generation backend.

Concretely:

1. Once you have run
   `python scripts/bootstrap_prompts.py --online` once, the prompt
   library lives entirely in this repository:

       data/prompts.sqlite
       data/prompts_comfy.jsonl
       data/prompts_raw.jsonl
       data/seed_prompts.jsonl  (always shipped, smallest fallback)

2. The router (`scripts/router.py`) reads **only** these files. It
   contains no `requests`, `urllib`, `httpx`, `socket.connect`, or
   any other network primitive. This is enforced by code review, not
   by runtime check — there is simply nothing to call out to.

3. `scripts/generate.py` calls the router, then calls a single
   adapter. The only adapter that may make an outbound HTTP call at
   runtime is the one explicitly chosen for image generation. The
   router itself does not.

## What "offline first" does NOT mean

It does **not** mean "the skill refuses to make network calls at
runtime". That would defeat ComfyUI, which is itself a local HTTP
service.

- **ComfyUI is local.** It is a service running on `127.0.0.1:8188`
  (or wherever the user configured). The skill talks to it over
  HTTP, but that traffic does not leave the machine. The machine
  can be completely offline and ComfyUI will still work.

- **SD WebUI is the same.** It is a local HTTP service. Same story.

- **Native image generation** is provided by the host agent. This
  skill just returns a `delegated` payload. The host agent may or
  may not make a network call to fulfil it; that is the host
  agent's concern, not this skill's.

- **Cloud image** is the only backend where the network is genuinely
  required. It is off by default and is a deliberate fallback.

## The single rule to remember

> If ComfyUI is configured and running, this skill works fully
> offline, end to end. "Offline" here means "no internet". ComfyUI's
> own localhost HTTP server does not count.

## How to verify offline operation

1. Disable Wi-Fi.
2. Make sure ComfyUI is running locally on
   `http://127.0.0.1:8188`.
3. Run:
   ```bash
   python scripts/generate.py "生成一个黑金风格的 AI 工具站宣传图" --backend auto
   ```
4. You should still get `status: "success"` and a list of output
   images, because ComfyUI was used.

Conversely, on a machine with internet but no ComfyUI, the same
command will walk down to `native_image` (returned as
`status: "delegated"`) or `prompt_only`.

## When the network IS used

Only in these places, only with explicit user opt-in:

| Where                                  | When           | Why                          |
|----------------------------------------|----------------|------------------------------|
| `scripts/bootstrap_prompts.py --online`| install/update | fetch the upstream prompt library |
| `adapters/cloud_image.py` `available()`| runtime, every call | DNS lookup only, no payload sent |
| `adapters/cloud_image.py` `generate()` | when selected  | returns a `delegated` payload; the host agent then performs the actual API call |
| `adapters/comfyui.py`                  | when selected  | localhost HTTP only          |
| `adapters/sd_webui.py`                 | when selected  | localhost HTTP only          |

No other component of the skill makes network calls.
