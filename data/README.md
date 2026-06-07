# Data directory

This directory stores local prompt data.

Files:

- `seed_prompts.jsonl`: small built-in seed prompt library for offline testing.
- `prompts_raw.jsonl`: imported raw prompt records.
- `prompts_comfy.jsonl`: converted backend-friendly prompt records.
- `prompts.sqlite`: searchable SQLite database.

The repository does not need network access after these files are generated.
