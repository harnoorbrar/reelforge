"""Image generation.

Free path (default): pollinations.ai text-to-image, no key, no cost.
Upgrade path: set FAL_KEY to route through FAL FLUX for higher fidelity.
"""
import time
import urllib.request
import urllib.parse
from pathlib import Path

from .config import FAL_KEY, IMAGE_W, IMAGE_H, POLLINATIONS_TIMEOUT, POLLINATIONS_RETRIES


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
    for attempt in range(POLLINATIONS_RETRIES + 1):
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
            wait = 6 * (attempt + 1)
            print(f"[images] pollinations HTTP {e.code}; retrying in {wait}s")
            time.sleep(wait)
        except Exception as e:
            last_err = e
            print(f"[images] pollinations attempt {attempt+1} failed: {e}")
            time.sleep(3)
    raise RuntimeError(f"pollinations image gen failed: {last_err}")


def _fal_image(prompt, out_path, width, height, seed):
    # Lazy import so the dependency is optional.
    from fal_client import sync_client  # placeholder; see README for FAL wiring
    raise NotImplementedError("Set FAL_KEY routing in images._fal_image per FAL docs")


if __name__ == "__main__":
    p = generate_image("a glowing neon city at night, vertical", "test.png")
    print("wrote", p)
