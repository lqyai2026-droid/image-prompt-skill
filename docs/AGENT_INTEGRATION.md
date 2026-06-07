# Agent integration

## Basic rule

Agents should call this skill when the user asks for image generation or image prompt preparation.

## Integration pattern

1. Call `scripts/generate.py` with the user's image request.
2. Use `--backend auto` by default.
3. If result status is `delegated`, the host agent should call its native image generation tool.
4. If result status is `prompt_only`, show the prompt or pass it to another image system.
5. If result status is `success`, return generated image paths or backend response.

## Example: host agent with native image generation

```bash
python scripts/generate.py "生成一个科技感网站首屏图" --backend native_image
```

The host agent receives a prompt and then uses its own image tool.

## Example: ComfyUI agent

```bash
python scripts/generate.py "生成一个产品主图" --backend comfyui
```

The skill patches the configured ComfyUI workflow and submits it to the API.

## Fallback behavior

Never fail only because ComfyUI is missing. Use `prompt_only` fallback.
