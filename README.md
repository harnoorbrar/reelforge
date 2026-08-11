# ReelForge 🎬

**Faceless TikTok / Reels video generator.** Type a topic → get a ready-to-post
9:16 AI video (script + voiceover + AI visuals + captions), with zero API keys to start.

Built as a zero-capital SaaS MVP. Runs on free generators out of the box
(edge-tts for voice, pollinations.ai for images, moviepy for assembly). Upgrade
any layer by adding a key.

## How it works
```
topic ─▶ scripts.py ─▶ voice.py (edge-tts)
                 └─▶ images.py (pollinations) ─▶ video.py (moviepy 9:16)
                                                          └─▶ reel.mp4
```

## Run locally
```bash
cd reelforge
uv venv .venv && source .venv/Scripts/activate     # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
python run.py
# open http://localhost:8000
```
`ffmpeg` must be on PATH (used by moviepy).

## API
| Method | Endpoint | Body | Returns |
|--------|----------|------|---------|
| POST | `/api/generate` | `{topic, scenes?, style?, voice?}` | `{job_id, status_url}` |
| GET  | `/api/status/<job_id>` | — | job status + result video URL |
| GET  | `/api/voices` | — | available TTS voices |
| GET  | `/healthz` | — | ok |

A full generation takes ~1.5–2.5 min (image gen is the slowest step on the
free tier). The first render on a cold free tier can be slower.

## Upgrade quality (all optional, all opt-in)
| Layer | Free default | Upgrade via env var |
|-------|--------------|----------------------|
| Scripts | template generator | `OPENAI_API_KEY` → LLM-written scripts |
| Images | pollinations `turbo` | `FAL_KEY` → FAL FLUX (sharper) |
| Voice | edge-tts (free) | `REEL_VOICE` to any edge-tts id |

## Deploy free
- **Render** (full app, recommended): import the repo, it reads `render.yaml`. Free tier.
- **Railway / Fly**: `Dockerfile` provided.
- **Netlify**: serve `static/index.html` as a landing page (wire it to a Render/API backend).

## Customer acquisition (zero-budget playbook)
1. **Show, don't tell** — every Reel you post IS the product. Use ReelForge to
   generate your own faceless content about `passive income`, `AI tools`, etc.
2. **Niche the offer**: target faceless-creator accounts, agencies, coaches.
3. **Post daily** to TikTok/Reels/Shorts with a CTA to the landing page.
4. **Free tier + watermark upsell** model: free 3-scene renders, paid removes
   watermark / unlocks more scenes & styles.
5. **Cold DM creators** offering "10 free Reels for your niche" in exchange for
   a testimonial.

## Project layout
```
src/
  config.py     settings + upgrade keys
  scripts.py    script generation (free template | OpenAI)
  voice.py      edge-tts voiceover
  images.py     pollinations image gen (+ FAL route)
  video.py      moviepy 9:16 assembly + captions + music
  pipeline.py   orchestrator + in-memory job store
  app.py        Flask API + landing page
run.py          entry point
static/index.html   landing page (has a live "Try it" demo)
```
