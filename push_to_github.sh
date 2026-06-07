#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${1:-https://github.com/lqyai2026-droid/image-prompt-skill.git}"

if [ ! -d .git ]; then
  git init
fi

git branch -M main
git add .
git commit -m "Initial portable image prompt skill" || echo "No changes to commit"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

git push -u origin main
