## tg_mini_app (Telegram Mini App для заказа суши)

Локальный каркас проекта: backend (FastAPI) + бот (aiogram) + SQLite.

### Быстрый старт (Windows)

Создать виртуальное окружение и установить зависимости:

```bash
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -e .
```

Создать `.env` из примера:

```bash
copy .env.example .env
```

Запуск API:

```bash
.venv\Scripts\python -m tg_mini_app.api
```

Запуск бота:

```bash
.venv\Scripts\python -m tg_mini_app.bot
```

### Сервер, systemd, GitHub

Пошаговые команды для VPS, совместный запуск API + бота, контроль процессов и работа с Git: [**docs/SERVER_RUNBOOK.md**](docs/SERVER_RUNBOOK.md).

