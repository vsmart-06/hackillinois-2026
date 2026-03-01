"""App configuration."""

import os
from pathlib import Path

# Load .env from project root or backend/ so MODAL_* and others are set
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# CIS API (public, no auth)
CIS_API_BASE = "http://courses.illinois.edu/cisapi"
DEFAULT_YEAR = "2024"
DEFAULT_SEMESTER = "fall"

# Local storage: one JSON file per subject under data/{year}/{semester}/{subject}.json
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Modal endpoints (optional). Set in env to enable /api/transcribe and /api/recommend.
# After: modal deploy modal/modal_whisper.py  and  modal deploy modal/modal_inference.py
MODAL_WHISPER_URL = os.environ.get("MODAL_WHISPER_URL", "").rstrip("/")
MODAL_INFERENCE_URL = os.environ.get("MODAL_INFERENCE_URL", "").rstrip("/")
