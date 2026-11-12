# Botu elle calistir (zamanlanmis gorevle ayni is)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "backend"
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\bot.py") @args
