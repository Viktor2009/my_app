#!/usr/bin/env bash
# Обновление tg_mini_app на Ubuntu VPS: git pull, зависимости, перезапуск systemd.
#
# Один запуск из каталога проекта:
#   cd /srv/tg_mini_app && bash deploy/server-update.sh
#
# После git clone первый раз (по желанию):
#   chmod +x deploy/server-update.sh
#   ./deploy/server-update.sh
#
# Переменные окружения (необязательно):
#   APP_ROOT=/srv/tg_mini_app   — корень репозитория (если скрипт вызывают не из него)
#   GIT_REMOTE=github           — имя remote (по умолчанию origin)
#   GIT_BRANCH=main
#   API_SERVICE / BOT_SERVICE   — имена unit-файлов systemd
#   NO_SYSTEMD_RESTART=1      — только pull и pip, без restart

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="${APP_ROOT:-$ROOT}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"
API_SERVICE="${API_SERVICE:-tg-mini-app-api.service}"
BOT_SERVICE="${BOT_SERVICE:-tg-mini-app-bot.service}"

cd "$APP_ROOT"

echo "==> $(pwd)"
echo "==> git pull $GIT_REMOTE $GIT_BRANCH"
git pull "$GIT_REMOTE" "$GIT_BRANCH"

if [[ ! -f .venv/bin/activate ]]; then
  echo "Ошибка: нет .venv. Создайте: python3 -m venv .venv" >&2
  exit 1
fi

# shellcheck source=/dev/null
source .venv/bin/activate

echo "==> pip install"
python -m pip install -q -U pip
python -m pip install -r requirements.txt
python -m pip install -e .

if [[ "${NO_SYSTEMD_RESTART:-0}" == "1" ]]; then
  echo "==> NO_SYSTEMD_RESTART=1 — systemd не трогаю"
  exit 0
fi

echo "==> sudo systemctl restart $API_SERVICE $BOT_SERVICE"
sudo systemctl restart "$API_SERVICE" "$BOT_SERVICE"
echo "==> status"
sudo systemctl status "$API_SERVICE" "$BOT_SERVICE" --no-pager
