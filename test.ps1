$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\backend"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m pytest tests -q
