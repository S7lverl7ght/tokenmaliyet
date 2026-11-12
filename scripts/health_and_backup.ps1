# Gunluk saglik kontrolu + sifreli yedek (rapor 4. tur bolum 6)
# Oracle Always Free bos kaynak geri alma politikasina karsi: her gun calisir.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$backupDir = Join-Path $root "data\backup"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

# 1) Saglik kontrolu
try {
    $r = Invoke-WebRequest "http://127.0.0.1:8000/health/full" -UseBasicParsing -TimeoutSec 20
    $j = $r.Content | ConvertFrom-Json
    Write-Host ("saglik: status={0} db={1} approved={2} yas={3}s" -f $j.status, $j.database, $j.approved_observations, $j.data_age_hours)
    if ($j.status -ne "ok") { Write-Warning "saglik durumu ok degil: $($j.status)" }
} catch {
    Write-Warning "saglik kontrolu basarisiz: $($_.Exception.Message)"
}

# 2) Sifreli pg_dump (GPG varsa sifrele, yoksa duz dump + uyari)
$env:PGPASSWORD = $env:PGPASSWORD
if (-not $env:PGPASSWORD) { $env:PGPASSWORD = "AiMaliyet2026Local" }
$raw = Join-Path $backupDir "ai_$stamp.dump"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h 127.0.0.1 -U ai_maliyet_user -Fc -f $raw ai_maliyet_merkezi 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) { Write-Error "pg_dump basarisiz"; exit 1 }

$gpg = Get-Command gpg -ErrorAction SilentlyContinue
if ($gpg) {
    & $gpg.Source --batch --yes --symmetric --cipher-algo AES256 --passphrase $env:BACKUP_PASSPHRASE -o "$raw.gpg" $raw 2>&1 | Out-Null
    if (Test-Path "$raw.gpg") { Remove-Item $raw -Force; Write-Host "sifreli yedek: $raw.gpg" }
} else {
    Write-Warning "gpg bulunamadi; yedek SIFRELENMEDI: $raw"
}

# 3) 14 gunden eski yedekleri temizle
Get-ChildItem $backupDir -Filter "ai_*" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "yedekleme tamam"
