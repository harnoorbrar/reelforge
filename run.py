"""ReelForge entry point. Run: python run.py  (after `source .venv/Scripts/activate`)"""
import os
import sys
from pathlib import Path

# Make sure the project root is importable.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("PORT", 8000)))
    print(f"ReelForge running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True, debug=False)
