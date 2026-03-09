#!/usr/bin/env bash
# Run the backend from the backend directory. Use this from backend/: ./run.sh
cd "$(dirname "$0")"
exec python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
