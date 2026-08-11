"""Flask app: API + static landing page.

Endpoints:
  GET  /                      -> landing page (static/index.html)
  POST /api/generate         -> {topic, scenes?, style?, voice?} -> {job_id}
  GET  /api/status/<job_id>  -> job status / result
  GET  /api/voices           -> available voices
  GET  /static/generated/... -> finished videos (served statically)
"""
import os
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, Response
from . import pipeline as pl
from .config import STATIC_DIR, BASE_DIR, VALID_VOICES

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")


INDEX = BASE_DIR / "static" / "index.html"


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/voices")
def voices():
    return jsonify({"voices": VALID_VOICES})


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    scenes = data.get("scenes")
    style = data.get("style", "cinematic")
    voice = data.get("voice")
    if voice and voice not in VALID_VOICES:
        voice = None

    job_id = pl.create_job(topic, scenes, style, voice)
    # Run off the request thread so the client can poll.
    t = threading.Thread(
        target=pl.run_job, args=(job_id, topic, scenes, style, voice), daemon=True
    )
    t.start()
    return jsonify({"job_id": job_id, "status_url": f"/api/status/{job_id}"})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = pl.JOBS.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    out = {
        "id": job["id"], "status": job["status"],
        "progress": job["progress"], "topic": job["topic"],
        "result": job["result"], "error": job["error"],
    }
    # Don't leak tracebacks to clients in production
    return jsonify(out)


@app.route("/healthz")
def health():
    return jsonify({"ok": True})


def main():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
