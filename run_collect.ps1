# Full daily pipeline: fetch -> pending -> QA -> (manual) approve
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\backend"
$py = "$PSScriptRoot\.venv\Scripts\python.exe"
& $py "$PSScriptRoot\scripts\collect.py"
& $py "$PSScriptRoot\scripts\collect_fx.py"
& $py "$PSScriptRoot\scripts\validate.py"
Write-Host "Run scripts\approve.py --list to review, then --auto or --ids to publish." -ForegroundColor Yellow
