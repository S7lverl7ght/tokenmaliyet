# TokenMaliyet fiyat botu - gunluk zamanlanmis gorev
# Kurulum: powershell -ExecutionPolicy Bypass -File scripts\install_bot_task.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$bot = Join-Path $root "scripts\bot.py"

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$bot`"" -WorkingDirectory $root
$trigger1 = New-ScheduledTaskTrigger -Daily -At 06:10
$trigger2 = New-ScheduledTaskTrigger -Daily -At 18:10
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName "TokenMaliyet-Fiyat-Botu" -Action $action -Trigger @($trigger1, $trigger2) -Settings $settings -Description "AI API ve GPU fiyatlarini toplar, QA ve esikli onay uygular." -Force | Out-Null
Write-Host "Gorev kuruldu: TokenMaliyet-Fiyat-Botu (06:10 ve 18:10)"
Write-Host "Elle calistirmak icin: .\scripts\bot.ps1"
