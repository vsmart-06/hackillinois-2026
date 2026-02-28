"""File storage for course data: one JSON file per subject under data/{year}/{semester}/{subject}.json."""

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .models import Course


def _subject_dir(year: str, semester: str) -> Path:
    d = DATA_DIR / year / semester
    d.mkdir(parents=True, exist_ok=True)
    return d


def path_for_subject(year: str, semester: str, subject: str) -> Path:
    """Path to the JSON file for a subject."""
    return _subject_dir(year, semester) / f"{subject}.json"


def save_courses(
    year: str,
    semester: str,
    subject: str,
    courses: list[Course] | list[dict[str, Any]],
) -> Path:
    """Save course list for a subject to JSON. Creates dirs if needed."""
    fp = path_for_subject(year, semester, subject)
    if courses and isinstance(courses[0], Course):
        data = [c.model_dump(by_alias=True) for c in courses]
    else:
        data = list(courses)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return fp


def load_courses(year: str, semester: str, subject: str) -> list[dict[str, Any]]:
    """Load course list for a subject from JSON. Returns empty list if missing."""
    fp = path_for_subject(year, semester, subject)
    if not fp.exists():
        return []
    return json.loads(fp.read_text(encoding="utf-8"))


def list_stored_subjects(year: str, semester: str) -> list[str]:
    """List subject codes that have stored JSON in data/{year}/{semester}/."""
    d = DATA_DIR / year / semester
    if not d.is_dir():
        return []
    return [p.stem for p in d.glob("*.json")]
