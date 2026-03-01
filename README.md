# Semflow

An LLM-powered product aiming to transform course selection for college students by handpicking courses that best align with their goals.

## Project layout

- **backend/** — FastAPI app (CIS catalog, storage, proxy to Modal).
- **modal/** — Modal apps: Whisper (speech → text) and Llama 3 8B (course recommendations).

## Backend (FastAPI + Pydantic)

- **CIS API**: Fetches course catalog from UIUC’s public [CIS API](https://courses.illinois.edu/cisdocs/api) (subjects → courses per subject: catalogue, subject, course number, title, description, prerequisites).
- **Storage**: One JSON file per subject under `backend/data/{year}/{semester}/{subject}.json`. Course dicts use `courseNumber` (and optional `avg_gpa` when you add grade data).
- **Endpoints**:
  - `GET /api/subjects?year=&semester=` — list all subjects (from CIS).
  - `GET /api/courses/{subject}?year=&semester=&source=storage|cis` — courses for a subject (from storage or live CIS).
  - `POST /api/ingest/subjects` — fetch subjects (no save).
  - `POST /api/ingest/courses/{subject}?save=true` — fetch courses for one subject and optionally save.
  - `POST /api/ingest/all` — fetch all subjects and all courses, save one JSON per subject.
  - `GET /api/storage/subjects` — list subjects that have stored JSON.
  - `GET /api/storage/courses/{subject}` — courses from storage only.
  - `POST /api/transcribe` — proxy to Modal Whisper; body `{ "audio_b64": "..." }`. Requires `MODAL_WHISPER_URL`.
  - `POST /api/recommend` — proxy to Modal Llama; body `goals`, `completed_courses`, optional `candidate_courses` or load from storage via `subject_codes` + `year`/`semester`. Requires `MODAL_INFERENCE_URL`.

### GPA data (one-time)

Recommendations include average GPA per course from [wadefagen/uiuc-gpa-dataset](https://github.com/wadefagen/datasets). Download the CSV once (not at runtime):

```bash
curl -o backend/data/uiuc-gpa-dataset.csv https://raw.githubusercontent.com/wadefagen/datasets/master/gpa/uiuc-gpa-dataset.csv
```

Then ensure `backend/data/` exists (e.g. run ingest once). The backend loads the CSV into memory on first use and enriches candidate courses with `avg_gpa` before sending them to the LLM.

### Run backend

```bash
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
cd backend
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive API.

### Optional: Modal (Whisper + Llama)

1. Install Modal and log in: `pip install modal` then `modal token new`.
2. Create a [Hugging Face token](https://huggingface.co/settings/tokens) with access to Meta-Llama-3-8B-Instruct, then in Modal dashboard create a secret named `huggingface-secret` with `HF_TOKEN`.
3. Deploy:
   - `modal deploy modal/modal_whisper.py`
   - `modal deploy modal/modal_inference.py`
4. Set env (or `.env` in backend) and restart the FastAPI server:
   - `MODAL_WHISPER_URL=<url from modal deploy>`
   - `MODAL_INFERENCE_URL=<url from modal deploy>`

See `.env.example` for a template.
