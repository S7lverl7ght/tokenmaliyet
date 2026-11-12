# Gunluk pg_dump yedegi (V0.1 kabul maddesi)
param([string]$OutDir = "$PSScriptRoot\..\data\backup")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $OutDir "ai_maliyet_merkezi_$stamp.dump"
$env:PGPASSWORD = "AiMaliyet2026Local"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h 127.0.0.1 -U ai_maliyet_user -Fc -f $out ai_maliyet_merkezi
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
Write-Host "yedek: $out"
Get-ChildItem $OutDir -Filter "*.dump" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -Force