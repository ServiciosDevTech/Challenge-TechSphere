#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d backend/.venv ]]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install --upgrade pip
  backend/.venv/bin/pip install -r backend/requirements.txt
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[setup] Se creó .env — agrega GOOGLE_API_KEY para el agente LLM."
fi

echo "[run] Backend en http://127.0.0.1:8000"
exec backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
