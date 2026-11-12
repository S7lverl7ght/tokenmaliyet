# Statik siteyi dist/ klasorune uretir (Cloudflare Pages'e yuklenebilir)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "backend"
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\export_static.py") @args
