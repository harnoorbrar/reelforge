"""Pipeline orchestrator: runs a full generation job end-to-end.

Job lifecycle (status): queued -> generating -> done | error
Outputs land in static/generated/<job_id>/ and are served statically.

PRODUCTION NOTES
----------------
* Job state is persisted to GENERATED_DIR/<job_id>/job.json so that status
  queries work correctly across multiple gunicorn workers (each worker has
  its own memory) and survive worker restarts.
* A bounded semaphore caps concurrent renders (moviepy/ffmpeg are heavy), so
  a flood of requests queues instead of spawning unbounded processes.
* All shared state access is guarded by a lock.
"""
import json
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import GENERATED_DIR
from .scripts import generate_script
from .voice import generate_voice
from .images import generate_image
from .video import build_video

# In-memory cache of job dicts (mirrors the on-disk JSON). Avoids re-reading
# the file on every status poll. Guarded by _lock.
_JOBS = {}
_lock = threading.Lock()

# Cap concurrent renders. ffmpeg + moviepy are CPU/RAM heavy; on a free-tier
# box, allow 2 at a time. Extra jobs wait in the queue (status stays "queued").
_MAX_CONCURRENT = 2
_slot = threading.Semaphore(_MAX_CONCURRENT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    return GENERATED_DIR / job_id / "job.json"


def _save(job: dict) -> None:
    """Persist a job dict to disk (atomic-ish: write then flush)."""
    with _lock:
        _JOBS[job["id"]] = job
        try:
            path = _job_path(job["id"])
            path.write_text(json.dumps(job, indent=2))
        except Exception as e:  # never let a save failure kill a job
            print("WARN: job save failed:", e)


def _load(job_id: str) -> dict | None:
    with _lock:
        if job_id in _JOBS:
            return _JOBS[job_id]
    # Fall back to disk (e.g. another worker created it).
    try:
        path = _job_path(job_id)
        if path.exists():
            job = json.loads(path.read_text())
            with _lock:
                _JOBS[job_id] = job
            return job
    except Exception:
        return None
    return None


def create_job(topic: str, num_scenes: int = None, style: str = "cinematic",
               voice: str = None) -> str:
    job_id = uuid.uuid4().hex[:12]
    work = GENERATED_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    job = {
        "id": job_id,
        "topic": topic,
        "status": "queued",
        "progress": "waiting in queue",
        "created": _now(),
        "updated": _now(),
        "result": None,
        "error": None,
    }
    _save(job)
    return job_id


def run_job(job_id: str, topic: str, num_scenes: int = None, style: str = "cinematic",
            voice: str = None):
    # Acquire a render slot; this blocks until one is free so concurrent
    # jobs queue rather than overload the box.
    _slot.acquire()
    try:
        _run_job_inner(job_id, topic, num_scenes, style, voice)
    finally:
        _slot.release()


def _run_job_inner(job_id: str, topic: str, num_scenes: int = None,
                  style: str = "cinematic", voice: str = None):
    job = _load(job_id)
    if not job:
        return
    try:
        work = GENERATED_DIR / job_id
        job["status"] = "generating"
        job["progress"] = "writing script"
        job["updated"] = _now()
        _save(job)

        job["progress"] = "generating voiceover"
        _save(job)

        script = generate_script(topic, num_scenes, style)
        (work / "script.json").write_text(json.dumps(script, indent=2))

        job["progress"] = "generating voiceover"
        _save(job)
        voice_path = generate_voice(script["total_voice"], work / "voice.mp3",
                                    voice=voice)

        job["progress"] = "generating visuals"
        _save(job)
        imgs = []
        for i, s in enumerate(script["scenes"]):
            # Serialized with a small gap to stay under the free image API's
            # rate limit (parallel bursts trigger HTTP 429).
            if i > 0:
                time.sleep(2.5)
            p = generate_image(s["image_prompt"], work / f"scene_{i:02d}.png")
            imgs.append(str(p))

        job["progress"] = "assembling 9:16 video"
        _save(job)
        out = build_video(script, imgs, voice_path, work / "reel.mp4",
                          music_path=None)

        job["status"] = "done"
        job["progress"] = "complete"
        job["updated"] = _now()
        job["result"] = {
            "video_url": f"/static/generated/{job_id}/reel.mp4",
            "script": script,
            "scenes": len(script["scenes"]),
            "duration_sec": _probe_duration(out),
        }
        _save(job)
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        job["trace"] = traceback.format_exc()
        job["updated"] = _now()
        _save(job)
        print("JOB FAILED", job_id, e)
        traceback.print_exc()


def get_job(job_id: str) -> dict | None:
    return _load(job_id)


def _probe_duration(path: Path) -> float | None:
    try:
        import subprocess
        out = subprocess.check_output([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(path)
        ])
        return float(json.loads(out)["format"]["duration"])
    except Exception:
        return None
