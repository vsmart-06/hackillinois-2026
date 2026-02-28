"""App configuration."""

from pathlib import Path

# CIS API (public, no auth)
CIS_API_BASE = "http://courses.illinois.edu/cisapi"
DEFAULT_YEAR = "2024"
DEFAULT_SEMESTER = "fall"

# Local storage: one JSON file per subject under data/{year}/{semester}/{subject}.json
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
