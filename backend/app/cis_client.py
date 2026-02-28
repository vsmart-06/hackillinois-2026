"""Client for UIUC CIS (Course Information Suite) public API.

API docs: https://courses.illinois.edu/cisdocs/api
Returns XML; we parse to our Pydantic models.
"""

import xml.etree.ElementTree as ET
from typing import Any
import httpx

from .config import CIS_API_BASE, DEFAULT_SEMESTER, DEFAULT_YEAR
from .models import Course, SubjectSummary

# XML namespaces used by CIS API (from docs)
NS = {"ns2": "http://rest.cis.illinois.edu"}


def _text(el: ET.Element | None, default: str = "") -> str:
    if el is not None and el.text:
        return (el.text or "").strip()
    return default


def _find_text(root: ET.Element, path: str, default: str = "") -> str:
    """Find first matching element and return its text. path is tag name or path."""
    el = root.find(path, NS)
    if el is None:
        el = root.find(path)
    return _text(el, default) if el is not None else default


def fetch_subjects(
    year: str = DEFAULT_YEAR,
    semester: str = DEFAULT_SEMESTER,
    *,
    client: httpx.Client | None = None,
) -> list[SubjectSummary]:
    """Fetch all subject codes for the given catalog term."""
    url = f"{CIS_API_BASE}/catalog/{year}/{semester}"
    url = f"{url}?mode=summary"
    close = False
    if client is None:
        client = httpx.Client(timeout=60.0)
        close = True
    try:
        resp = client.get(url, headers={"Accept": "application/xml"})
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        out: list[SubjectSummary] = []
        prefix = f"/catalog/{year}/{semester}/"
        seen: set[str] = set()
        # Summary mode returns subject links; structure may be subjectSummary or subject
        for subj in root.iter():
            if subj.tag.endswith("subjectSummary") or subj.tag.endswith("subject"):
                sid = subj.get("id") or ""
                href = subj.get("href", "")
                if not sid and href and prefix in href:
                    parts = href.rstrip("/").split("/")
                    # Subject link: .../catalog/year/semester/SUBJECT (no course number)
                    if len(parts) >= 1 and parts[-1] and "/" not in parts[-1]:
                        sid = parts[-1]
                label = _find_text(subj, "label") or _text(subj) or sid or ""
                if sid and sid not in seen:
                    seen.add(sid)
                    out.append(SubjectSummary(id=sid, href=href, label=label or sid))
        # Fallback: any href that is exactly catalog/year/semester/SUBJECT (one segment after semester)
        if not out:
            for el in root.iter():
                href = el.get("href", "")
                if not href or prefix not in href:
                    continue
                parts = href.rstrip("/").split("/")
                try:
                    i = parts.index("catalog")
                except ValueError:
                    continue
                # catalog, year, semester, subject -> 4 segments, so subject at i+3 and nothing after
                if i + 4 != len(parts):
                    continue
                sid = (parts[i + 3] or "").strip()
                if sid and len(sid) <= 10 and sid not in seen:
                    seen.add(sid)
                    out.append(SubjectSummary(id=sid, href=href, label=_text(el) or sid))
        return out
    finally:
        if close:
            client.close()


def _parse_course(
    course_el: ET.Element,
    catalogue: str,
    subject: str,
) -> Course | None:
    """Parse one course element from subject/course list or course detail."""
    # Course number often in id or in a child
    cid = course_el.get("id", "")
    href = course_el.get("href", "")
    if not cid and href:
        parts = href.rstrip("/").split("/")
        cid = parts[-1] if parts else ""
    label = _find_text(course_el, "label") or _text(course_el) or cid
    # If we have a link to full course, we could fetch it for description/prereqs; here we use inline if present
    description = _find_text(course_el, "description") or _find_text(course_el, "courseDescription")
    prerequisites = _find_text(course_el, "prerequisite") or _find_text(course_el, "prerequisites")
    # Title often in label (e.g. "125 - Introduction to Computer Science")
    title = label
    if " - " in label:
        title = label.split(" - ", 1)[1].strip()
    return Course(
        catalogue=catalogue,
        subject=subject,
        course_number=cid or "?",
        title=title or cid or "Unknown",
        description=description,
        prerequisites=prerequisites,
    )


def fetch_courses_for_subject(
    subject: str,
    year: str = DEFAULT_YEAR,
    semester: str = DEFAULT_SEMESTER,
    *,
    client: httpx.Client | None = None,
) -> list[Course]:
    """Fetch all courses for one subject. Fetches subject summary then each course for full details."""
    catalogue = f"{year}/{semester}"
    url = f"{CIS_API_BASE}/catalog/{year}/{semester}/{subject}"
    url_summary = f"{url}?mode=summary"
    close = False
    if client is None:
        client = httpx.Client(timeout=60.0)
        close = True
    try:
        # Get list of course ids in this subject
        resp = client.get(url_summary, headers={"Accept": "application/xml"})
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        course_ids: list[str] = []
        for el in root.iter():
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if tag in ("course", "courseSummary"):
                cid = el.get("id")
                if cid:
                    course_ids.append(cid)
                else:
                    href = el.get("href", "")
                    if f"/{subject}/" in href:
                        parts = href.rstrip("/").split("/")
                        if len(parts) >= 2:
                            course_ids.append(parts[-1])
        course_ids = list(dict.fromkeys(course_ids))

        courses: list[Course] = []
        for cid in course_ids:
            detail_url = f"{CIS_API_BASE}/catalog/{year}/{semester}/{subject}/{cid}"
            try:
                r2 = client.get(detail_url, headers={"Accept": "application/xml"})
                r2.raise_for_status()
                detail_root = ET.fromstring(r2.text)
                # Full course detail has description, prerequisite, etc.
                desc = _find_text(detail_root, "description") or _find_text(detail_root, "courseDescription")
                prereq = _find_text(detail_root, "prerequisite") or _find_text(detail_root, "prerequisites")
                label = _find_text(detail_root, "label") or _find_text(detail_root, "title")
                title = label
                if label and " - " in label:
                    title = label.split(" - ", 1)[1].strip()
                if not title:
                    title = _find_text(detail_root, "title") or cid
                courses.append(
                    Course(
                        catalogue=catalogue,
                        subject=subject,
                        course_number=cid,
                        title=title or cid,
                        description=desc,
                        prerequisites=prereq,
                    ),
                )
            except (httpx.HTTPError, ET.ParseError):
                # Fallback: use summary info only
                courses.append(
                    Course(
                        catalogue=catalogue,
                        subject=subject,
                        course_number=cid,
                        title=cid,
                        description="",
                        prerequisites="",
                    ),
                )
        return courses
    finally:
        if close:
            client.close()


def fetch_all_courses(
    year: str = DEFAULT_YEAR,
    semester: str = DEFAULT_SEMESTER,
    *,
    client: httpx.Client | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch all subjects, then all courses per subject. Returns dict subject -> list of course dicts."""
    subjects = fetch_subjects(year=year, semester=semester, client=client)
    catalogue = f"{year}/{semester}"
    result: dict[str, list[dict[str, Any]]] = {}
    for s in subjects:
        subj_id = s.id
        courses = fetch_courses_for_subject(subj_id, year=year, semester=semester, client=client)
        result[subj_id] = [c.model_dump(by_alias=True) for c in courses]
    return result
