# Запуск API + cloudflared в отдельных окнах. Бот — отдельно после обновления BASE_URL.
# Запуск из корня проекта:  pwsh -File scripts\dev-start.ps1
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
$cf = Join-Path $root "cloudflared.exe"
if (-not (Test-Path $py)) {
    Write-Error "Нет $py — создайте venv и pip install -r requirements.txt"
    exit 1
}
if (-not (Test-Path $cf)) {
    Write-Error "Положите cloudflared.exe в корень проекта: $cf"
    exit 1
}

& (Join-Path $root "scripts\dev-stop.ps1")

Start-Sleep -Seconds 1

Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root'; & '$py' -m tg_mini_app.api"
) -WorkingDirectory $root

Start-Sleep -Seconds 2

Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root'; & '$cf' tunnel --url http://127.0.0.1:8000"
) -WorkingDirectory $root

Write-Host ""
Write-Host "1) В окне cloudflared скопируйте https://....trycloudflare.com"
Write-Host "2) Вставьте в .env в строку BASE_URL="
Write-Host "3) Запустите бота:"
Write-Host "   pwsh -File scripts\dev-bot.ps1"
Write-Host "   или вручную: .venv\Scripts\python -m tg_mini_app.bot"
Write-Host ""
