# Queens Connect Web Chat – Backend

FastAPI server that keeps the ADK agent loaded once at startup and serves `POST /chat`.

## Run (from repo root)

```bash
# Terminal 1 – from repo root
cd /path/to/queeny
pip install -r backend/requirements.txt
# Ensure .env or backend/queens_connect/.env has GOOGLE_API_KEY (or GEMINI_API_KEY)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or from the `backend` folder:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend: from repo root, `cd frontend && npm install && npm run dev` (Terminal 2).
