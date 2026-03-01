# Semflow: What’s in the project and how it links together

## What the project is

Semflow is a **course recommendation system for UIUC**: the user gives **goals/interests** and **courses already completed**; the system suggests **what to take now** and **what to work toward**, using the real catalog (CIS) and an LLM (Llama on Modal). Optionally, the user can speak instead of type (Whisper on Modal).

---

## What the project has (by layer)

| Layer | What it is | Where it lives |
|-------|------------|----------------|
| **Data source** | UIUC CIS public API (catalog: subjects, courses, descriptions, prerequisites) | External: `courses.illinois.edu/cisapi` |
| **Local cache** | One JSON file per subject so we don’t hit CIS every time | `backend/data/{year}/{semester}/{subject}.json` |
| **Backend API** | Single FastAPI app: catalog, storage, ingest, and proxy to Modal | `backend/app/` (main.py, config, models, cis_client, storage) |
| **Speech → text** | Whisper on GPU (Modal) | `modal/modal_whisper.py` (deployed to Modal) |
| **Recommendations** | Llama 3 8B on GPU (Modal) | `modal/modal_inference.py` (deployed to Modal) |
| **Frontend** | Not built yet; will call the backend API | (Your UI) |

---

## How everything links together

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (your UI – not in repo yet)                                    │
│  - Text or speech input (goals, completed courses)                       │
│  - Calls: POST /api/transcribe (if voice), POST /api/recommend          │
│  - Also: GET /api/subjects, GET /api/courses/{subject}, ingest endpoints│
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTP
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)  —  single entry point                                │
│  - Serves catalog (from CIS or from storage)                             │
│  - Ingest: fetch from CIS → save to backend/data/                       │
│  - Proxy: /api/transcribe → Modal Whisper                                │
│  - Proxy: /api/recommend  → Modal Llama (candidates from storage or body)│
└───────┬─────────────────────────────┬─────────────────────┬────────────┘
        │                             │                     │
        ▼                             ▼                     ▼
┌───────────────┐           ┌─────────────────┐    ┌─────────────────────┐
│  CIS API      │           │  backend/data/  │    │  MODAL (cloud GPUs)  │
│  (UIUC)       │           │  JSON per       │    │  - Whisper (speech)  │
│  subjects,    │  ingest   │  subject        │    │  - Llama (recommend) │
│  courses      │ ────────►│                 │    │  URLs set in env     │
└───────────────┘           └─────────────────┘    └─────────────────────┘
```

- **Frontend** talks only to the **FastAPI backend** (one origin, one place for CORS and auth later).
- **Backend** talks to **CIS** (to fetch catalog), to **disk** (to read/write course JSON), and to **Modal** (only if `MODAL_WHISPER_URL` / `MODAL_INFERENCE_URL` are set).
- **Course shape** is the same everywhere: `subject`, `courseNumber`, `title`, `description`, `prerequisites` (and optional `avg_gpa` later). Storage and Modal both use this shape.

---

## End-to-end flows

### 1. Ingest catalog (one-time or periodic)

- You (or a script) call **POST /api/ingest/all** (or ingest per subject).
- Backend uses **cis_client** to hit **CIS API** for that term, then **storage** writes **backend/data/{year}/{semester}/{subject}.json** for each subject.
- After that, **GET /api/courses/{subject}** with `source=storage` is fast and doesn’t call CIS.

### 2. Speech input (optional)

- User records audio in the frontend.
- Frontend sends base64 audio to **POST /api/transcribe**.
- Backend forwards to **Modal Whisper** (`MODAL_WHISPER_URL`). Whisper returns text.
- Frontend uses that text as goals or “completed courses” in the next step.

### 3. Get recommendations

- Frontend sends **POST /api/recommend** with:
  - **goals** (string),
  - **completed_courses** (e.g. `["CS 225", "MATH 241"]`),
  - optionally **subject_codes** and **year** / **semester** (to build candidates from storage), or **candidate_courses** (list of course dicts) directly.
- If you don’t send `candidate_courses`, the backend uses **storage** (`load_courses_for_subjects`) to load course dicts from **backend/data/** for that term (and optional subject filter).
- Backend forwards goals + completed_courses + candidate_courses to **Modal Llama** (`MODAL_INFERENCE_URL`). Llama returns **can_take_now** and **work_toward**.
- Backend returns that JSON to the frontend.

So: **catalog and storage** feed **candidate_courses**; **goals + completed_courses** come from the user (text or speech). One backend ties CIS, storage, and Modal together.

---

## File map (what does what)

| File / folder | Role |
|---------------|------|
| **backend/app/main.py** | FastAPI app: all routes (catalog, ingest, storage, /api/transcribe, /api/recommend). |
| **backend/app/config.py** | CIS base URL, default year/semester, data dir, `MODAL_WHISPER_URL` / `MODAL_INFERENCE_URL` (from env). |
| **backend/app/models.py** | Pydantic: `Course`, `SubjectSummary`, `CatalogTerm` (same shape as API and storage). |
| **backend/app/cis_client.py** | HTTP + XML parsing for CIS: fetch subjects, fetch courses per subject. |
| **backend/app/storage.py** | Read/write course JSON under `backend/data/`; `load_courses_for_subjects` for recommend. |
| **modal/modal_whisper.py** | Modal app: Whisper web endpoint; called by backend when `MODAL_WHISPER_URL` is set. |
| **modal/modal_inference.py** | Modal app: Llama 3 8B web endpoint; called by backend when `MODAL_INFERENCE_URL` is set. |
| **.env.example** | Template for Modal URLs (and any future env). |
| **.venv** | Python venv; backend runs with this (see README). |

---

## What you need to run the full flow

1. **Backend**: `source .venv/bin/activate`, `cd backend`, `uvicorn app.main:app --reload`. Catalog + storage + proxy routes work immediately; no Modal needed for ingest or listing courses.
2. **Modal (optional)**:
   - Deploy `modal/modal_whisper.py` and `modal/modal_inference.py`, set `MODAL_WHISPER_URL` and `MODAL_INFERENCE_URL` (e.g. from `.env`).
   - Then **POST /api/transcribe** and **POST /api/recommend** work end-to-end.
3. **Frontend**: Not in repo; it just calls the backend API as above.

That’s the full picture: one backend, one data shape, CIS + local storage + optional Modal for speech and recommendations.
