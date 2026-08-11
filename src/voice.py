"""Voice generation via edge-tts (free, no API key, no signup)."""
import asyncio
from pathlib import Path

import edge_tts
from .config import VOICE


def generate_voice(text: str, out_path, voice: str = None) -> Path:
    voice = voice or VOICE
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async def _speak():
        comm = edge_tts.Communicate(text, voice)
        await comm.save(str(out_path))

    asyncio.run(_speak())
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("edge-tts produced no audio")
    return out_path


if __name__ == "__main__":
    p = generate_voice("This is a test of the voice generator.", "test.mp3")
    print("wrote", p)
