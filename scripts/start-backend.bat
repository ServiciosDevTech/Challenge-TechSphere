@echo off
setlocal
cd /d "%~dp0.."

if not exist "backend\.venv\Scripts\python.exe" (
  echo [setup] Creando entorno virtual...
  python -m venv backend\.venv
  backend\.venv\Scripts\python -m pip install --upgrade pip
  backend\.venv\Scripts\pip install -r backend\requirements.txt
)

if not exist ".env" (
  copy .env.example .env >nul
  echo [setup] Se creo .env — agrega GOOGLE_API_KEY cuando vayas a usar el agente LLM.
)

echo [run] Backend en http://127.0.0.1:8000
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
