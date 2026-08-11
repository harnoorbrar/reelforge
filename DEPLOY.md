# Deploy ReelForge to a LIVE URL (one-time, needs your GitHub account)

The code is built, tested, and committed locally in /c/Users/noori/reelforge.
To get a public URL you only need to (1) create a GitHub repo and (2) push.
Then deploy free on Render (reads render.yaml automatically).

## Option A — let the agent do it (paste a token)
Set a GitHub personal access token (repo scope) as an env var, then tell me:
    export GITHUB_TOKEN=ghp_xxxx
and I'll run the push + give you the Render import link. (I can't read your
token from here, so this is the one step only you can perform.)

## Option B — you run it (2 minutes)
1. Go to https://github.com/new  →  create repo named `reelforge` (Public).
2. In a terminal at C:\Users\noori\reelforge run:
       git remote add origin https://github.com/<YOURUSER>/reelforge.git
       git branch -M main
       git push -u origin main
3. Go to https://render.com → New → Web Service → connect the repo.
   Render auto-detects render.yaml (free tier, builds + deploys).
   Your live URL: https://reelforge.onrender.com

## Live test after deploy
   POST https://reelforge.onrender.com/api/generate
        {"topic":" passive income for beginners","scenes":3,"style":"neon"}
   then GET  https://reelforge.onrender.com/api/status/<job_id>

## Cost
   $0. Free image/voice generators built in. Upgrade later with optional
   OPENAI_API_KEY (scripts) and FAL_KEY (sharper images) env vars in Render.
