# Gunluk toplama + yedek gorevi (kullanici oturumunda calisir, yonetici gerekmez)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$root\run_collect.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 09:15
Register-ScheduledTask -TaskName "AI-Maliyet-Merkezi-Gunluk" -Action $action -Trigger $trigger -Force | Out-Null
$baction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$root\scripts\backup_db.ps1`""
$btrigger = New-ScheduledTaskTrigger -Daily -At 09:45
Register-ScheduledTask -TaskName "AI-Maliyet-Merkezi-Yedek" -Action $baction -Trigger $btrigger -Force | Out-Null
Write-Host "Gorevler kuruldu: AI-Maliyet-Merkezi-Gunluk (09:15), AI-Maliyet-Merkezi-Yedek (09:45)"
Write-Host "Not: toplama sonrasi onay adimi elle calistirilir -> scripts\approve.py --auto"