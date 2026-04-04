"""Абсолютные пути к ресурсам пакета (не зависят от cwd при запуске)."""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT: Path = Path(__file__).resolve().parent
# Репозиторий: .../tg_mini_app (рядом лежат .env, data/, pyproject.toml).
PROJECT_ROOT: Path = PACKAGE_ROOT.parent.parent
TEMPLATES_DIR: Path = PACKAGE_ROOT / "templates"
STATIC_DIR: Path = PACKAGE_ROOT / "static"
ENV_FILE: Path = PROJECT_ROOT / ".env"
