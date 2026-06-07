# Deploy

## Local deployment

```bash
git clone https://github.com/lqyai2026-droid/image-prompt-skill.git
cd image-prompt-skill
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
python scripts/convert_prompts.py
python scripts/generate.py "生成一个黑金风格的高端 AI 工具站宣传图" --backend prompt_only
```

## Import GPT-Image-2 prompt source

```bash
python scripts/import_repo.py --repo-url https://github.com/EvoLinkAI/awesome-gpt-image-2-API-and-Prompts.git
python scripts/convert_prompts.py
```

After this, `data/prompts.sqlite` can be used offline.

## Upload this starter to GitHub manually

```bash
git init
git branch -M main
git add .
git commit -m "Initial portable image prompt skill"
git remote add origin https://github.com/lqyai2026-droid/image-prompt-skill.git
git push -u origin main
```

If the remote already has commits:

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```
