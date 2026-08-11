"""Script generation.

Free path (default): a deterministic, decent template generator that turns a
topic into a hook + N scene captions + voiceover lines. No API key needed.

Upgrade path: set OPENAI_API_KEY to use a real LLM for richer scripts.
"""
import os
import json
import urllib.request
from .config import OPENAI_API_KEY, LLM_MODEL, DEFAULT_SCENES, MAX_SCENES


def generate_script(topic: str, num_scenes: int = None, style: str = "cinematic") -> dict:
    num_scenes = num_scenes or DEFAULT_SCENES
    num_scenes = max(2, min(MAX_SCENES, int(num_scenes)))
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("A topic is required.")

    if OPENAI_API_KEY:
        try:
            return _openai_script(topic, num_scenes, style)
        except Exception as e:  # fall back to free generator on any LLM error
            print(f"[scripts] LLM failed ({e}); using free generator.")
    return _template_script(topic, num_scenes, style)


def _template_script(topic: str, n: int, style: str) -> dict:
    t = topic.strip().lower()
    hook = f"POV: you tried {t} and your feed changed forever"

    captions = ["the truth", "why most fail", "the real method"]
    voices = [
        f"Here is the truth about {t} that nobody on the internet talks about.",
        f"Most people get {t} wrong, and it costs them every single day.",
        f"The method that actually works for {t} is stupidly simple.",
    ]
    style_note = {
        "cinematic": "cinematic photo, film still",
        "anime": "anime illustration, bold colors",
        "minimal": "clean minimal flat illustration, soft pastel",
        "neon": "neon cyberpunk, dark, glowing accents",
    }.get(style, "cinematic photo, film still")

    scenes = []
    for i in range(n):
        cap = captions[i % len(captions)]
        voice = voices[i % len(voices)]
        img_prompt = (
            f"{style_note}, vertical 9:16, scene {i+1} about {cap}, "
            f"high detail, no text, no watermark"
        )
        scenes.append({"caption": cap, "voice": voice, "image_prompt": img_prompt})

    return {
        "topic": topic,
        "hook": hook,
        "style": style,
        "scenes": scenes,
        "total_voice": " ".join(s["voice"] for s in scenes),
    }


def _openai_script(topic: str, n: int, style: str) -> dict:
    system = (
        "You are a short-form video scriptwriter for faceless TikTok/Reels. "
        "Given a topic and a number of scenes, return ONLY valid JSON: "
        "{\"hook\": str, \"scenes\": [{\"caption\": str, \"voice\": str, "
        "\"image_prompt\": str}], \"style\": str}. Captions are <6 words, "
        "punchy. Voice lines are one spoken sentence each. image_prompt is a "
        "detailed vertical 9:16 visual description with no text."
    )
    user = f"Topic: {topic}\nScenes: {n}\nVisual style: {style}"
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read())
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    parsed["topic"] = topic
    # normalise
    if "scenes" not in parsed or not parsed["scenes"]:
        raise ValueError("LLM returned no scenes")
    return parsed


if __name__ == "__main__":
    import pprint
    pprint.pprint(generate_script("morning routine for focus", 4, "neon"))
