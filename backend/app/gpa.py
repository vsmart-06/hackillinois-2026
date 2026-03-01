"""Load UIUC GPA dataset (CSV) once, expose in-memory lookup and enrich_courses_with_gpa()."""

import csv
from pathlib import Path
from typing import Any

from .config import DATA_DIR

# CSV path: backend/data/uiuc-gpa-dataset.csv (download once, never at runtime)
GPA_CSV_PATH = DATA_DIR / "uiuc-gpa-dataset.csv"

# Grade points (UIUC 4.0 scale); W excluded from GPA
_GRADE_POINTS = {
    "A+": 4.0,
    "A": 4.0,
    "A-": 3.67,
    "B+": 3.33,
    "B": 3.0,
    "B-": 2.67,
    "C+": 2.33,
    "C": 2.0,
    "C-": 1.67,
    "D+": 1.33,
    "D": 1.0,
    "D-": 0.67,
    "F": 0.0,
}

# Lazy-loaded: (subject, number) -> average GPA (float)
_gpa_by_course: dict[tuple[str, str], float] | None = None


def _int(val: Any) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def _load_gpa_table() -> dict[tuple[str, str], float]:
    """Load CSV once; build (Subject, Number) -> weighted average GPA."""
    global _gpa_by_course
    if _gpa_by_course is not None:
        return _gpa_by_course

    if not GPA_CSV_PATH.exists():
        _gpa_by_course = {}
        return _gpa_by_course

    # Per (Subject, Number): sum of (grade_points * count) and sum of students for GPA
    total_points: dict[tuple[str, str], float] = {}
    total_students: dict[tuple[str, str], float] = {}

    grade_cols = [c for c in _GRADE_POINTS]

    with open(GPA_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject = (row.get("Subject") or "").strip().upper()
            number = str(_int(row.get("Number", 0))).strip()
            if not subject or not number:
                continue
            key = (subject, number)
            row_pts = 0.0
            row_students = 0
            for g, pts in _GRADE_POINTS.items():
                cnt = _int(row.get(g, 0))
                row_pts += pts * cnt
                row_students += cnt
            if row_students == 0:
                continue
            total_points[key] = total_points.get(key, 0) + row_pts
            total_students[key] = total_students.get(key, 0) + row_students

    _gpa_by_course = {}
    for key in total_points:
        s = total_students.get(key, 0)
        if s > 0:
            _gpa_by_course[key] = round(total_points[key] / s, 2)
    return _gpa_by_course


def get_avg_gpa(subject: str, number: str) -> float | None:
    """Return average GPA for course (subject, number) or None if not in dataset."""
    table = _load_gpa_table()
    key = (subject.strip().upper(), str(number).strip())
    return table.get(key)


def enrich_courses_with_gpa(courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add avg_gpa to each course dict (in place and return).
    Course dict must have 'subject' and 'courseNumber' (or 'number'). Missing GPA stays absent or becomes 'N/A'.
    """
    table = _load_gpa_table()
    for c in courses:
        subj = (c.get("subject") or "").strip().upper()
        num = str(c.get("courseNumber") or c.get("number") or "").strip()
        gpa = table.get((subj, num)) if subj and num else None
        c["avg_gpa"] = round(gpa, 2) if gpa is not None else "N/A"
    return courses
