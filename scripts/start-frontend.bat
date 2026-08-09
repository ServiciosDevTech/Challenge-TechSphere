@echo off
setlocal
cd /d "%~dp0..\frontend"

if not exist "node_modules" (
  echo [setup] Instalando dependencias del frontend...
  call npm install
)

echo [run] Frontend en http://127.0.0.1:5173
call npm run dev -- --host 127.0.0.1 --port 5173
