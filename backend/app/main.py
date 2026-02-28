"""Semflow backend: FastAPI app and API to link frontend and CIS course data."""

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_SEMESTER, DEFAULT_YEAR
from .cis_client import fetch_courses_for_subject, fetch_subjects, fetch_all_courses
from .models import Course, SubjectSummary
from .storage import load_courses, list_stored_subjects, save_courses


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optional: shared httpx client for fetch routes
    async with httpx.AsyncClient(timeout=60.0) as client:
        app.state.http_client = client
        yield
    # client closed on exit


app = FastAPI(
    title="Semflow API",
    description="Course data and recommendations for UIUC (CIS catalog + local storage)",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Catalog (CIS API) ----------


@app.get("/api/subjects", response_model=list[SubjectSummary])
async def get_subjects(
    year: str = Query(DEFAULT_YEAR, description="Catalog year (e.g. 2024)"),
    semester: str = Query(DEFAULT_SEMESTER, description="One of spring, summer, fall"),
):
    """Retrieve all subjects for the given catalog term from the CIS API."""
    try:
        # Sync client used in cis_client; could refactor to async later
        subjects = fetch_subjects(year=year, semester=semester)
        return subjects
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CIS API error: {e!s}") from e


@app.get("/api/courses/{subject}", response_model=list[dict[str, Any]])
async def get_courses_by_subject(
    subject: str,
    year: str = Query(DEFAULT_YEAR, description="Catalog year"),
    semester: str = Query(DEFAULT_SEMESTER, description="spring, summer, or fall"),
    source: str = Query("storage", description="'storage' = local JSON; 'cis' = fetch from CIS API"),
):
    """
    Get courses for a subject. Use source=storage for cached JSON files,
    or source=cis to fetch live from the CIS API (and optionally save).
    """
    if source == "storage":
        data = load_courses(year, semester, subject)
        return data
    if source == "cis":
        try:
            courses = fetch_courses_for_subject(subject, year=year, semester=semester)
            return [c.model_dump(by_alias=True) for c in courses]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"CIS API error: {e!s}") from e
    raise HTTPException(status_code=400, detail="source must be 'storage' or 'cis'")


# ---------- Ingest: fetch from CIS and save to files ----------


@app.post("/api/ingest/subjects")
async def ingest_subjects(
    year: str = Query(DEFAULT_YEAR),
    semester: str = Query(DEFAULT_SEMESTER),
):
    """Fetch all subjects from CIS and return the list (no file write)."""
    try:
        subjects = fetch_subjects(year=year, semester=semester)
        return {"year": year, "semester": semester, "subjects": [s.model_dump() for s in subjects]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CIS API error: {e!s}") from e


@app.post("/api/ingest/courses/{subject}")
async def ingest_subject_courses(
    subject: str,
    year: str = Query(DEFAULT_YEAR),
    semester: str = Query(DEFAULT_SEMESTER),
    save: bool = Query(True, description="Write to data/{year}/{semester}/{subject}.json"),
):
    """Fetch all courses for one subject from CIS; optionally save to local JSON."""
    try:
        courses = fetch_courses_for_subject(subject, year=year, semester=semester)
        if save:
            save_courses(year, semester, subject, courses)
        return {
            "year": year,
            "semester": semester,
            "subject": subject,
            "count": len(courses),
            "courses": [c.model_dump(by_alias=True) for c in courses],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CIS API error: {e!s}") from e


@app.post("/api/ingest/all")
async def ingest_all(
    year: str = Query(DEFAULT_YEAR),
    semester: str = Query(DEFAULT_SEMESTER),
):
    """
    Fetch all subjects, then all courses per subject from CIS, and save
    one JSON file per subject under data/{year}/{semester}/{subject}.json.
    """
    try:
        all_data = fetch_all_courses(year=year, semester=semester)
        for subj, course_list in all_data.items():
            save_courses(year, semester, subj, course_list)
        return {
            "year": year,
            "semester": semester,
            "subjects": list(all_data.keys()),
            "counts": {s: len(c) for s, c in all_data.items()},
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CIS API error: {e!s}") from e


# ---------- Local storage ----------


@app.get("/api/storage/subjects", response_model=list[str])
async def stored_subjects(
    year: str = Query(DEFAULT_YEAR),
    semester: str = Query(DEFAULT_SEMESTER),
):
    """List subject codes that have stored course JSON for this term."""
    return list_stored_subjects(year, semester)


@app.get("/api/storage/courses/{subject}", response_model=list[dict[str, Any]])
async def stored_courses(
    subject: str,
    year: str = Query(DEFAULT_YEAR),
    semester: str = Query(DEFAULT_SEMESTER),
):
    """Get courses for a subject from local JSON only."""
    return load_courses(year, semester, subject)


# ---------- Health ----------


@app.get("/health")
async def health():
    return {"status": "ok"}
