#!/usr/bin/env bash
# ReelForge one-shot deploy. Run AFTER creating an empty GitHub repo named "reelforge".
# Usage:  GITHUB_TOKEN=ghp_xxx  GH_USER=yourname  ./deploy.sh
set -euo pipefail

: "${GITHUB_TOKEN:?Set GITHUB_TOKEN (repo scope)}"
: "${GH_USER:?Set GH_USER to your GitHub username}"

REPO="reelforge"
REMOTE="https://${GITHUB_TOKEN}@github.com/${GH_USER}/${REPO}.git"

cd "$(dirname "$0")"

echo "[1/3] ensuring branch is 'main'"
git branch -M main

echo "[2/3] pushing to github.com/${GH_USER}/${REPO}"
git push -u "$REMOTE" main

echo "[3/3] done. Now deploy free on Render:"
echo "  1. Go to https://render.com -> New -> Web Service -> connect ${GH_USER}/${REPO}"
echo "  2. Render auto-reads render.yaml (free tier). Build + deploy starts automatically."
echo "  3. Your live URL: https://${REPO}.onrender.com"
echo ""
echo "Live smoke test after deploy:"
echo "  curl -X POST https://${REPO}.onrender.com/api/generate \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"topic\":\"passive income for beginners\",\"scenes\":3,\"style\":\"neon\"}'"
