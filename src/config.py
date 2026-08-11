"""ReelForge configuration. All generators degrade to FREE, no-API-key paths
by default. Set env vars to upgrade quality (OpenAI for scripts, FAL for images)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
GENERATED_DIR = STATIC_DIR / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# --- Script generation ---
# If OPENAI_API_KEY is present, scripts use the LLM. Otherwise a free
# template generator runs (no key, no cost).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

# --- Voice generation (edge-tts, always free, no key) ---
VOICE = os.environ.get("REEL_VOICE", "en-US-AriaNeural")
VALID_VOICES = [
    "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural",
    "en-GB-SoniaNeural", "en-AU-NatashaNeural", "en-IN-NeerjaNeural",
]

# --- Image generation ---
# Default: pollinations.ai (free, no key). Set FAL_KEY to upgrade to FAL FLUX.
# Source images are generated at 720x1280 (fast on free tier) and upscaled to
# 1080x1920 in the video assembly — TikTok-grade quality at ~2x the speed.
FAL_KEY = os.environ.get("FAL_KEY")
IMAGE_W, IMAGE_H = 720, 1280

# --- Video ---
VIDEO_W, VIDEO_H = 1080, 1920
MAX_SCENES = 5
DEFAULT_SCENES = 3

# --- Pipeline tuning ---
POLLINATIONS_TIMEOUT = 150
POLLINATIONS_RETRIES = 2
