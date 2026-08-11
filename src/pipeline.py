"""Pipeline orchestrator: runs a full generation job end-to-end.

Job lifecycle (status): queued -> generating -> done | error
Outputs land in static/generated/<job_id>/ and are served statically.
"""
import json
import shutil
import tempfile
import traceback
import uuid
import time
from pathlib import Path

from .config import GENERATED_DIR
from .scripts import generate_script
from .voice import generate_voice
from .images import generate_image
from .video import build_video

JOBS = {}  # job_id -> dict (in-memory; fine for MVP / single-instance)


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()[:40]


def create_job(topic: str, num_scenes: int = None, style: str = "cinematic",
               voice: str = None) -> str:
    job_id = uuid.uuid4().hex[:12]
    work = GENERATED_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    JOBS[job_id] = {
        "id": job_id,
        "topic": topic,
        "status": "queued",
        "progress": "waiting in queue",
        "created": _now(),
        "result": None,
        "error": None,
    }
    return job_id


def run_job(job_id: str, topic: str, num_scenes: int = None, style: str = "cinematic",
            voice: str = None):
    job = JOBS.get(job_id)
    if not job:
        return
    try:
        work = GENERATED_DIR / job_id
        job["status"] = "generating"

        job["progress"] = "writing script"
        script = generate_script(topic, num_scenes, style)
        (work / "script.json").write_text(json.dumps(script, indent=2))

        job["progress"] = "generating voiceover"
        voice_path = generate_voice(script["total_voice"], work / "voice.mp3",
                                    voice=voice)

        job["progress"] = "generating visuals"
        imgs = []
        for i, s in enumerate(script["scenes"]):
            # Serialized with a small gap to stay under the free image API's
            # rate limit (parallel bursts trigger HTTP 429).
            if i > 0:
                time.sleep(2.5)
            p = generate_image(s["image_prompt"], work / f"scene_{i:02d}.png")
            imgs.append(str(p))

        job["progress"] = "assembling 9:16 video"
        out = build_video(script, imgs, voice_path, work / "reel.mp4",
                         music_path=None)

        job["status"] = "done"
        job["progress"] = "complete"
        rel = f"/static/generated/{job_id}/reel.mp4"
        job["result"] = {
            "video_url": rel,
            "script": script,
            "scenes": len(script["scenes"]),
            "duration_sec": _probe_duration(out),
        }
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        job["trace"] = traceback.format_exc()
        print("JOB FAILED", job_id, e)
        traceback.print_exc()


def _now():
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def _probe_duration(path: Path) -> float | None:
    try:
        import subprocess, json as _json
        out = subprocess.check_output([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(path)
        ])
        return float(_json.loads(out)["format"]["duration"])
    except Exception:
        return None
