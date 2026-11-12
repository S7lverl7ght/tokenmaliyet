# Start the read-only FastAPI service on 127.0.0.1:8000
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\backend"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
