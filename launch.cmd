@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The local runtime is missing. Run setup.ps1 while online first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.main
if errorlevel 1 pause
