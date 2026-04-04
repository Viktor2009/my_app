# Останавливает API, бота и cloudflared для локальной разработки (Windows).
$ErrorActionPreference = "SilentlyContinue"
Get-Process cloudflared | Stop-Process -Force
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match 'tg_mini_app' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-NetTCPConnection -LocalPort 8000 -State Listen |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Write-Host "Остановлено: cloudflared, tg_mini_app (Python), порт 8000."
