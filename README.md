# Semflow

An LLM-powered product aiming to transform course selection for college students by handpicking courses that best align with their goals.

## Backend (FastAPI + Pydantic)

- **CIS API**: Fetches course catalog from UIUC’s public [CIS API](https://courses.illinois.edu/cisdocs/api) (subjects → courses per subject with catalogue, subject, course number, title, description, prerequisites).
- **Storage**: One JSON file per subject under `backend/data/{year}/{semester}/{subject}.json`.
- **Endpoints**:
  - `GET /api/subjects?year=&semester=` — list all subjects (from CIS).
  - `GET /api/courses/{subject}?year=&semester=&source=storage|cis` — courses for a subject (from storage or live CIS).
  - `POST /api/ingest/subjects` — fetch subjects (no save).
  - `POST /api/ingest/courses/{subject}?save=true` — fetch courses for one subject and optionally save.
  - `POST /api/ingest/all` — fetch all subjects and all courses, save one JSON per subject.
  - `GET /api/storage/subjects` — list subjects that have stored JSON.
  - `GET /api/storage/courses/{subject}` — courses from storage only.

### Run

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive API.
