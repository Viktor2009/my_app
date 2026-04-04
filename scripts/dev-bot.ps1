# Запуск только бота (после того как BASE_URL в .env обновлён).
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root'; & '$py' -m tg_mini_app.bot"
) -WorkingDirectory $root
