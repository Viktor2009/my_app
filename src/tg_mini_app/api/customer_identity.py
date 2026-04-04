"""Определение Telegram user id клиента Mini App (initData / отладка)."""

from __future__ import annotations

from fastapi import HTTPException

from tg_mini_app.api.telegram_webapp import (
    InitDataValidationError,
    validate_init_data_and_get_user_id,
)
from tg_mini_app.settings import Settings


def webapp_signing_secret(settings: Settings) -> str:
    """Материал для HMAC initData: TELEGRAM_WEBAPP_SECRET или BOT_TOKEN."""
    if (settings.telegram_webapp_secret or "").strip():
        return settings.telegram_webapp_secret.strip()
    return (settings.bot_token or "").strip()


def allow_customer_tg_id_fallback(settings: Settings) -> bool:
    """Только APP_ENV=local: customer_tg_id без подписанного initData."""
    return (settings.app_env or "").strip().lower() == "local"


def resolve_customer_tg_id(
    init_data: str | None,
    customer_tg_id: int | None,
    *,
    settings: Settings,
) -> int:
    """Общая логика для заказов, корзины и отмены."""
    raw = (init_data or "").strip() or None
    if raw:
        secret = webapp_signing_secret(settings)
        try:
            return validate_init_data_and_get_user_id(
                raw,
                signing_secret=secret,
                max_auth_age_sec=settings.webapp_init_max_age_sec,
            ).id
        except InitDataValidationError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e
    if customer_tg_id is not None and not allow_customer_tg_id_fallback(settings):
        raise HTTPException(
            status_code=422,
            detail=(
                "Без подписанного initData передан только customer_tg_id, а на сервере "
                "APP_ENV не local. Откройте Mini App кнопкой в боте или для отладки в "
                "браузере задайте в .env APP_ENV=local "
                "(BOT_TOKEN должен быть от того же бота, что и кнопка Web App)."
            ),
        )
    if allow_customer_tg_id_fallback(settings) and customer_tg_id is not None:
        return customer_tg_id
    raise HTTPException(
        status_code=422,
        detail=(
            "Нужен подписанный initData (поле init_data в JSON, опционально заголовок "
            "X-Telegram-Init-Data). Откройте витрину из Telegram (кнопка Web App в боте), не "
            "через обычный браузер. Локальная отладка: APP_ENV=local и поле «Telegram ID» "
            "на странице."
        ),
    )


def assert_cart_mutation_allowed(cart_owner_tg_id: int | None, caller_tg_id: int) -> None:
    """Если у корзины задан владелец — менять может только он."""
    if cart_owner_tg_id is None:
        return
    if cart_owner_tg_id != caller_tg_id:
        raise HTTPException(status_code=403, detail="Это не ваша корзина")
