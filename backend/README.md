# Queens Connect Web Chat – Backend

FastAPI server that keeps the ADK agent loaded once at startup and serves `POST /chat`.

## Run

**From the `backend` directory** (recommended):

```bash
cd backend
pip install -r requirements.txt
# Ensure .env or queens_connect/.env has GOOGLE_API_KEY (or GEMINI_API_KEY)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Do **not** use `uvicorn backend.main:app` when your current directory is `backend` — that requires the repo root to be on `PYTHONPATH` (see below).

**From repo root** (alternative):

```bash
cd /path/to/queeny
pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend: from repo root, `cd frontend && npm install && npm run dev` (Terminal 2).
