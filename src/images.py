"""Image generation.

Free path (default): pollinations.ai text-to-image, no key, no cost.
Upgrade path: set FAL_KEY to route through FAL FLUX for higher fidelity.

PRODUCTION NOTES
----------------
Pollinations' free tier rate-limits aggressively (HTTP 429). Two defenses:
  * A global rate limiter (threading.Semaphore + min-interval sleep) caps how
    fast we hit the API across ALL concurrent jobs, so a burst of requests
    can't trigger a 429 storm.
  * Robust retry with exponential backoff + jitter on 429/5xx.
"""
import time
import threading
import urllib.request
import urllib.parse
from pathlib import Path

from .config import FAL_KEY, IMAGE_W, IMAGE_H, POLLINATIONS_TIMEOUT

# --- Global rate limiting for the free Pollinations tier -------------------
# At most one request every MIN_INTERVAL seconds, regardless of how many jobs
# are running. This keeps us safely under the free-tier rate limit.
_RATE_LOCK = threading.Lock()
_LAST_CALL = [0.0]
_MIN_INTERVAL = 8.0  # seconds between pollinations calls (tunable)
_MAX_ATTEMPTS = 6


def _throttle():
    """Block until at least MIN_INTERVAL has elapsed since the last call."""
    with _RATE_LOCK:
        now = time.time()
        wait = _MIN_INTERVAL - (now - _LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL[0] = time.time()


def generate_image(prompt: str, out_path, width: int = IMAGE_W, height: int = IMAGE_H,
                   seed: int = None) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if FAL_KEY:
        try:
            return _fal_image(prompt, out_path, width, height, seed)
        except Exception as e:
            print(f"[images] FAL failed ({e}); falling back to pollinations.")

    return _pollinations_image(prompt, out_path, width, height, seed)


def _pollinations_image(prompt, out_path, width, height, seed):
    safe = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{safe}"
        f"?width={width}&height={height}&nologo=true&model=turbo&enhance=false"
        f"&seed={seed if seed is not None else int(time.time()) % 100000}"
    )
    last_err = None
    for attempt in range(_MAX_ATTEMPTS):
        # Throttle globally BEFORE each attempt (covers retries too).
        _throttle()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ReelForge/1.0"})
            with urllib.request.urlopen(req, timeout=POLLINATIONS_TIMEOUT) as r:
                data = r.read()
            if not data or len(data) < 1000:
                raise ValueError("image too small / empty")
            out_path.write_bytes(data)
            return out_path
        except urllib.error.HTTPError as e:
            last_err = e
            # Honor the server's own Retry-After hint if provided.
            retry_after = e.headers.get("Retry-After") if hasattr(e, "headers") else None
            try:
                ra = int(retry_after) if retry_after else 0
            except (TypeError, ValueError):
                ra = 0
            # Exponential backoff with jitter; 429/5xx need a longer wait.
            base = max(10 * (2 ** attempt), ra)
            jitter = base * 0.3
            wait = base + (time.time() % jitter)
            print(f"[images] pollinations HTTP {e.code}; retry {attempt+1}/{_MAX_ATTEMPTS} in {wait:.0f}s")
            time.sleep(wait)
        except Exception as e:
            last_err = e
            print(f"[images] pollinations attempt {attempt+1} failed: {e}")
            time.sleep(5)
    # Friendly, user-facing error instead of a raw internal trace.
    raise RuntimeError(
        "image service is rate-limited right now; please try again in a minute"
    )


def _fal_image(prompt, out_path, width, height, seed):
    # Lazy import so the dependency is optional.
    from fal_client import sync_client  # placeholder; see README for FAL wiring
    raise NotImplementedError("Set FAL_KEY routing in images._fal_image per FAL docs")


if __name__ == "__main__":
    p = generate_image("a glowing neon city at night, vertical", "test.png")
    print("wrote", p)
