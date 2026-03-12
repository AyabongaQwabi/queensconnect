## Queens Connect – WhatsApp Super App (Komani/Queenstown)

Queens Connect is a hyper-local **WhatsApp-first super app** for Komani/Queenstown townships.  
It combines community info, marketplace listings, lending, and payments – all inside one WhatsApp number – using:

- **WhatsApp Cloud API** → webhook into Firebase Cloud Functions
- **Firebase (Firestore, Auth, Cloud Functions, Storage)** as the main app backend
- **Python ADK agent backend** on FastAPI (Render) for AI orchestration and tools
- **React frontend** for web admin/ops and debugging

This README covers the **whole monorepo**: how folders fit together, how to run things locally, and how to deploy.

---

## 1. Repo Structure

- `backend/` – FastAPI backend, ADK agents and tools, serves the built React app in production.
- `frontend/` – React/Vite SPA used for web UI and ops.
- `functions/` – Firebase Cloud Functions (TypeScript) for WhatsApp webhooks, callable APIs, lending flows, and scheduled jobs.
- `whatsapp/` – WhatsApp Cloud API sandbox, testing tools, and related config (if present).
- `docs/` – Architecture plans, prompts, schema docs, deployment notes (start with `docs/things-to-build.md`).
- `firebase.json`, `firestore.rules`, `storage.rules`, `firestore.indexes.json` – Firebase project config.
- `render.yaml` – Render template for deploying the Python backend + frontend as a single web service.

See `backend/README.md` for backend-only details.

---

## 2. Prerequisites

- **Node.js** ≥ 18 (for `frontend/` and `functions/`)
- **Python** 3.11 (matches `.python-version`)
- **Firebase CLI** (`npm install -g firebase-tools`)
- **Google Cloud SDK** (optional but useful for credentials)
- Accounts/keys:
  - Firebase project (Firestore, Storage, Functions enabled)
  - Google AI / Gemini API key (`GOOGLE_API_KEY` or `GEMINI_API_KEY`)
  - Optional: Groq, xAI, Ikhokha, Twilio, etc. (see `docs/deploy-render.md`)

---

## 3. Environment Set‑up

### 3.1 Backend (FastAPI + ADK)

1. Copy `backend/queens_connect/.env.example` to `.env` (same folder) and fill in:
   - `GOOGLE_API_KEY` / `GEMINI_API_KEY`
   - `FIREBASE_PROJECT_ID` (if different from default)
   - Any other API keys you plan to use.
2. (Optional on local) Point to Firebase emulator by setting `FIRESTORE_EMULATOR_HOST` as described in `.env.example`.

### 3.2 Firebase

1. In the Firebase Console, create a project (or use `queens-connect-2c94d`).
2. Enable **Firestore**, **Functions**, **Authentication (Phone)**, and **Storage**.
3. Make sure `firebase.json`, `firestore.rules`, `storage.rules` match your project/bucket (see `docs/firebase-storage-cv.md`).

---

## 4. Running Locally

### 4.1 Backend API (FastAPI)

From repo root:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Alternatively (from repo root):

```bash
pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

See `backend/README.md` for more context.

### 4.2 Frontend (React)

From repo root:

```bash
cd frontend
npm install          # or npm ci
npm run dev          # Vite dev server, usually on http://localhost:5173
```

You can set `VITE_API_URL` to point at your FastAPI server:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

### 4.3 Firebase Functions (WhatsApp + APIs)

From repo root:

```bash
cd functions
npm install          # or npm ci
npm run build
firebase emulators:start --only functions
```

Useful scripts (from `functions/package.json`):

- `npm run serve` – build then start Firebase emulators for functions.
- `npm run deploy` – deploy Cloud Functions to your Firebase project.

The main function entrypoints live in `functions/src/index.ts` (WhatsApp webhook, callable APIs, scheduled jobs).

---

## 5. Deployment

### 5.1 Backend + Frontend on Render

This project is set up to deploy as a **single Render Web Service**. Render runs the FastAPI backend and serves the built React app.

High‑level steps:

1. Push the repo to GitHub/GitLab.
2. In Render, create a **Web Service** from this repo (or use `render.yaml` as a blueprint).
3. Set environment variables as described in `docs/deploy-render.md`:
   - Core AI keys (`GOOGLE_API_KEY`, etc.)
   - Firebase (`FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, etc.)
   - Optional payment/search keys.
4. Deploy – Render will:
   - Install backend dependencies.
   - Build the React app (`frontend/dist`).
   - Start `gunicorn backend.main:app` bound to `$PORT`.

See `docs/deploy-render.md` for full details.

### 5.2 Firebase (Firestore, Storage, Functions)

From repo root:

```bash
firebase login
firebase use <your-project-id>

# Deploy rules and indexes
firebase deploy --only firestore:rules,firestore:indexes,storage

# Deploy Cloud Functions
cd functions
npm run build
firebase deploy --only functions
```

Check `docs/firebase-storage-cv.md` for Storage bucket naming and configuration.

---

## 6. WhatsApp Cloud API Flow (High Level)

End‑to‑end message path:

1. **WhatsApp user** sends a message.
2. **Meta Cloud API** POSTs webhook to Firebase HTTPS function:
   - `functions/src/index.ts` → `webhookWhatsApp`.
3. Cloud Function validates signature, then:
   - Logs payload.
   - Calls into the Python ADK backend / orchestrator (planned) or responds directly.
4. ADK agents read/write data in **Firestore** using the tools in `backend/queens_connect/tools/`.
5. Responses go back to the user via WhatsApp Cloud API.

More architecture detail lives in `docs/things-to-build.md` and the various prompt docs under `docs/prompts/`.

---

## 7. Where to Start Reading Code

- **Firebase Cloud Functions:** `functions/src/index.ts`
- **Python backend config:** `backend/queens_connect/config.py`
- **AI tools (Firestore, CVs, gamification, etc.):** `backend/queens_connect/tools/`
- **Architecture overview:** `docs/things-to-build.md`
- **Deployment to Render:** `docs/deploy-render.md`

---

## 8. Contributing

- Keep prompts and business rules in sync with the docs under `docs/`.
- When adding new tools or functions:
  - Prefer small, composable functions with clear names.
  - Update this README or the relevant sub‑README (`backend/README.md`, etc.).
- Avoid committing secrets (`.env`, service account JSON). Use environment variables or secret managers.

