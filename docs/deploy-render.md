# Deploying Queens Connect on Render

The app runs as a single **Web Service** on Render: the FastAPI backend serves the API and the built React SPA from one process.

## Quick deploy

1. Push the repo to GitHub/GitLab and connect it in [Render](https://dashboard.render.com).
2. Create a **Web Service** and use the **Blueprint** from the repo (or add the repo and Render will detect `render.yaml`).
3. Set the required **Environment** variables in the Render dashboard (see below).
4. Deploy. Render runs the build, then starts the app; `/health` is used for health checks.

## Build and start (from `render.yaml`)

- **Build:** `pip install -r backend/requirements.txt` then `cd frontend && npm ci && npm run build`. The React app is built into `frontend/dist`, which the backend serves.
- **Start:** `gunicorn backend.main:app` with a uvicorn worker, bound to `$PORT`. Render sets `PORT` automatically.

## Environment variables

Set these in the Render service **Environment** tab. Secrets (API keys) should be marked **Secret**.

### Required

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI / Gemini API key (or `GEMINI_API_KEY`) |
| `GROQ_API_KEY` | Groq API key (sub-agents / Llama via LiteLLM) |
| `XAI_API_KEY` | xAI API key (Grok kasi-voice rewrite) |

### Firebase

| Variable | Description |
|----------|-------------|
| `FIREBASE_PROJECT_ID` | Default: `queens-connect-2c94d`; set if different |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase service account JSON, or provide credentials via Render’s secret files / env (see [Firebase on Render](https://render.com/docs/firebase)) |

**Important:** Do **not** set `FIRESTORE_EMULATOR_HOST` on Render. When unset, the app uses production Firestore. If you see "using Firestore emulator" in logs, remove that env var from Render and redeploy.

### Optional

| Variable | Description |
|----------|-------------|
| `LENDING_BASE_URL` or `BASE_URL` | **Recommended.** Public URL of this app (e.g. `https://queens-connect.onrender.com`). Used for payment callbacks and proof-of-payment links. |
| `TWILIO_AUTH_TOKEN` | Validate Twilio webhook signatures |
| `YOCO_SECRET_KEY` | Yoco payment links (loan unlock fees) |
| `SERPAPI_KEY` | SerpAPI for search tools |
| `MODEL`, `GROQ_MODEL`, `GROK_MODEL` | Override default models |

## Frontend API URL

The React app is served from the same origin as the API on Render, so it can use relative URLs for the API. If you set `VITE_API_URL` at **build time** (e.g. in Render env as `VITE_API_URL=https://your-service.onrender.com`), the frontend will target that base URL. For same-origin deployment, you can leave it unset or set it to the Render URL so it’s correct after deploy.

## Python version

The repo includes `.python-version` (3.11). You can override with the `PYTHON_VERSION` env var in Render if needed.
