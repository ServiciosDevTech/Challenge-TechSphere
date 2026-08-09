#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

if [[ ! -d node_modules ]]; then
  npm install
fi

echo "[run] Frontend en http://127.0.0.1:5173"
exec npm run dev -- --host 127.0.0.1 --port 5173
