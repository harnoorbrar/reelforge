"""End-to-end smoke test of the ReelForge pipeline.
Generates a real 9:16 video from a topic and prints the result path."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import src.pipeline as pl

TOPIC = "why your phone battery dies so fast"
print("=== ReelForge smoke test ===")
print("topic:", TOPIC)
t0 = time.time()
job_id = pl.create_job(TOPIC, num_scenes=4, style="cinematic")
print("job_id:", job_id)
pl.run_job(job_id, TOPIC, num_scenes=4, style="cinematic")
job = pl.get_job(job_id)
print("status:", job["status"])
print("progress:", job["progress"])
if job["status"] == "done":
    r = job["result"]
    print("video_url:", r["video_url"])
    print("scenes:", r["scenes"], "duration:", r["duration_sec"], "s")
    out = Path(__file__).resolve().parent / "static" / "generated" / job_id / "reel.mp4"
    print("file exists:", out.exists(), "size:", out.stat().st_size if out.exists() else 0)
    print(f"elapsed: {time.time()-t0:.1f}s")
else:
    print("ERROR:", job.get("error"))
    print(job.get("trace", ""))
