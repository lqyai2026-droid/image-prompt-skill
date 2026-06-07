# Universal Image Prompt Skill

## Purpose

This skill helps any agent create better image-generation prompts by using a local prompt library and backend adapters.

It can:

1. understand a natural-language image request;
2. search a local prompt library;
3. rewrite the request for a target image backend;
4. route the request to ComfyUI, Stable Diffusion WebUI, a host agent's native image generation capability, or prompt-only output;
5. work without absolute paths.

## When to use

Use this skill whenever the user asks to create, generate, render, draw, design, visualize, or prepare a prompt for an image.

Examples:

- “帮我生成一个公众号封面”
- “做一个黑金风格 AI 工具站宣传图”
- “生成一个产品广告图”
- “给 ComfyUI 写一个提示词”
- “把这个想法变成 Midjourney/Flux/SDXL 提示词”

## Core rule

Do not assume a fixed backend.

Choose backend in this order unless the user specifies one:

1. native image generation of the host agent, if available;
2. ComfyUI, if configured and reachable;
3. Stable Diffusion WebUI, if configured and reachable;
4. prompt_only fallback.

## Required behavior

When called, the skill should:

1. parse the user intent;
2. infer category, aspect ratio, style, and image purpose;
3. retrieve a prompt template from the local library;
4. produce backend-specific prompt text;
5. call the selected backend if possible;
6. if no backend can generate images, return the final prompt instead of failing.

## Backend output formats

### prompt_only

Return a copyable prompt and metadata.

### native_image

Return:

```json
{
  "status": "delegated",
  "backend": "native_image",
  "prompt": "...",
  "instruction": "Host agent should call its native image generation capability with this prompt."
}
```

Do not pretend the image was generated.

### comfyui

Return a ComfyUI-ready positive prompt, negative prompt, width, height, model suggestion, workflow profile, and generated file paths if available.

### sd_webui

Return txt2img API result or a structured error.

## Path policy

Never hard-code paths such as `/home/user/...` or `/home/lqyai/...`.

Use:

1. CLI path argument;
2. `IMAGE_PROMPT_SKILL_HOME`;
3. repository root;
4. relative paths from `config.yaml`.

## Failure policy

If a configured backend is unavailable, route to the next backend. `prompt_only` must always be available.
