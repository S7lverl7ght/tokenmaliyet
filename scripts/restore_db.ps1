# Yedekten geri yukleme provasi: ayri veritabanina restore edip satir sayisini dogrular
param([Parameter(Mandatory=$true)][string]$Dump, [string]$TargetDb = "ai_maliyet_restore_test")
# NOT: psql NOTICE mesajlarini stderr'e yazar; Stop modu bunu hata sayar.
$ErrorActionPreference = "Continue"
$env:PGPASSWORD = "AiMaliyet2026Local"
$pg = "C:\Program Files\PostgreSQL\18\bin"
& "$pg\psql.exe" -h 127.0.0.1 -U ai_maliyet_user -d postgres -c "DROP DATABASE IF EXISTS $TargetDb;" | Out-Null
& "$pg\psql.exe" -h 127.0.0.1 -U ai_maliyet_user -d postgres -c "CREATE DATABASE $TargetDb;" | Out-Null
& "$pg\pg_restore.exe" -h 127.0.0.1 -U ai_maliyet_user -d $TargetDb --no-owner $Dump
& "$pg\psql.exe" -h 127.0.0.1 -U ai_maliyet_user -d $TargetDb -t -c "SELECT 'approved=' || count(*) FROM price_observations WHERE status='approved';"
Write-Host "restore provasi tamam: $TargetDb"