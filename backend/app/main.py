"""Semflow backend: FastAPI app and API to link frontend and CIS course data."""

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_SEMESTER, DEFAULT_YEAR, MODAL_INFERENCE_URL, MODAL_WHISPER_URL
from .cis_client import fetch_courses_for_subject, fetch_subjects, fetch_all_courses
from .models import Course, SubjectSummary
from .storage import (
    load_courses,
    load_courses_for_subjects,
    list_stored_subjects,
    save_courses,
)
from .gpa import enrich_courses_with_gpa


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


# ---------- Modal: Whisper (speech) and Llama (recommendations) ----------


@app.post("/api/transcribe")
async def transcribe(payload: dict) -> dict:
    """
    Proxy to Modal Whisper. POST body: { "audio_b64": "<base64 audio>" }.
    Requires MODAL_WHISPER_URL to be set (deploy with: modal deploy modal/modal_whisper.py).
    """
    if not MODAL_WHISPER_URL:
        raise HTTPException(
            status_code=503,
            detail="Modal Whisper not configured. Set MODAL_WHISPER_URL and deploy modal/modal_whisper.py",
        )
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(MODAL_WHISPER_URL, json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Modal Whisper error: {e!s}") from e


@app.post("/api/recommend")
async def recommend(payload: dict) -> dict:
    """
    Proxy to Modal Llama inference. POST body:
    - goals (required): string
    - completed_courses (required): list of strings e.g. ["CS 225", "MATH 241"]
    - candidate_courses (optional): list of course dicts (subject, courseNumber, title, description, prerequisites).
      If omitted, loaded from storage using year/semester and subject_codes (or all stored subjects).
    - subject_codes (optional): list of subject codes to use as candidates when candidate_courses not provided
    - year, semester (optional): for loading candidates from storage; default from config.

    Requires MODAL_INFERENCE_URL to be set (deploy with: modal deploy modal/modal_inference.py).
    """
    if not MODAL_INFERENCE_URL:
        raise HTTPException(
            status_code=503,
            detail="Modal inference not configured. Set MODAL_INFERENCE_URL and deploy modal/modal_inference.py",
        )
    goals = payload.get("goals", "")
    completed_courses = payload.get("completed_courses", [])
    candidate_courses = payload.get("candidate_courses")
    subject_codes = payload.get("subject_codes")
    year = payload.get("year", DEFAULT_YEAR)
    semester = payload.get("semester", DEFAULT_SEMESTER)

    if not goals:
        raise HTTPException(status_code=400, detail="goals is required")

    if candidate_courses is None:
        candidate_courses = load_courses_for_subjects(year, semester, subject_codes)
        if not candidate_courses:
            raise HTTPException(
                status_code=400,
                detail="No candidate courses. Ingest courses (POST /api/ingest/all or /api/ingest/courses/{subject}) or pass candidate_courses.",
            )

    # Inject average GPA from local CSV so the LLM sees it
    candidate_courses = enrich_courses_with_gpa(list(candidate_courses))

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(
                MODAL_INFERENCE_URL,
                json={
                    "goals": goals,
                    "completed_courses": completed_courses,
                    "candidate_courses": candidate_courses,
                },
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Modal inference error: {e!s}") from e


# ---------- Health ----------


@app.get("/health")
async def health():
    return {"status": "ok"}
