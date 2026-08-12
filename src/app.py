"""Flask app: API + static landing page.

Endpoints:
  GET  /                      -> landing page (static/index.html)
  POST /api/generate         -> {topic, scenes?, style?, voice?} -> {job_id}
  GET  /api/status/<job_id>  -> job status / result
  GET  /api/voices           -> available voices
  GET  /healthz              -> liveness probe (no deps)
  GET  /static/generated/... -> finished videos (served statically)

Production notes:
  * Served via gunicorn (see Procfile / render.yaml). The dev server in
    run.py is for local use only.
  * Job state lives on disk (pipeline._save) so status queries are correct
    across multiple gunicorn workers.
  * /api/status never returns internal tracebacks to clients.
"""
import os
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, Response
from . import pipeline as pl
from .config import STATIC_DIR, BASE_DIR, VALID_VOICES

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")

# Reject oversized bodies early (prevent abusive payloads).
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB is plenty for JSON topic

INDEX = BASE_DIR / "static" / "index.html"

# Gunicorn may spawn multiple worker processes; a single worker-scope lock is
# enough for request handling since job state is file-backed.
_app_lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/voices")
def voices():
    return jsonify({"voices": VALID_VOICES})


@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400

    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    if len(topic) > 120:
        return jsonify({"error": "topic too long (max 120 chars)"}), 400

    scenes = data.get("scenes")
    if scenes is not None:
        try:
            scenes = int(scenes)
        except (TypeError, ValueError):
            scenes = None
        if scenes is not None and not (1 <= scenes <= 5):
            return jsonify({"error": "scenes must be between 1 and 5"}), 400

    style = (data.get("style") or "cinematic").strip()
    voice = data.get("voice")
    if voice and voice not in VALID_VOICES:
        voice = None

    job_id = pl.create_job(topic, scenes, style, voice)
    # Run off the request thread so the client can poll; daemon so it never
    # blocks shutdown. Concurrency is capped inside run_job via a semaphore.
    t = threading.Thread(
        target=pl.run_job, args=(job_id, topic, scenes, style, voice), daemon=True
    )
    t.start()
    return jsonify({"job_id": job_id, "status_url": f"/api/status/{job_id}"})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = pl.get_job(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    # Never leak internal tracebacks to clients.
    job = {k: v for k, v in job.items() if k != "trace"}
    return jsonify(job)


@app.route("/healthz")
def health():
    return jsonify({"ok": True})


def main():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
