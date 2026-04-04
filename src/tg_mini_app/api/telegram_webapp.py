from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


@dataclass(frozen=True, slots=True)
class WebAppUser:
    id: int


class InitDataValidationError(ValueError):
    pass


def _secret_key(signing_secret: str) -> bytes:
    # https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    return hmac.new(
        key=b"WebAppData",
        msg=signing_secret.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()


def validate_init_data_and_get_user_id(
    init_data: str,
    *,
    signing_secret: str,
    max_auth_age_sec: int = 86400,
) -> WebAppUser:
    """
    Проверка подписи Telegram WebApp initData и извлечение user.id.

    signing_secret — по документации Telegram это токен бота; в .env можно задать
    TELEGRAM_WEBAPP_SECRET (тот же секрет), иначе используется BOT_TOKEN.
    """
    if not init_data:
        raise InitDataValidationError("init_data пустой")
    if not signing_secret.strip():
        raise InitDataValidationError(
            "Для проверки init_data задайте BOT_TOKEN или TELEGRAM_WEBAPP_SECRET",
        )

    data = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise InitDataValidationError("hash отсутствует")

    pairs = [f"{k}={v}" for k, v in sorted(data.items(), key=lambda kv: kv[0])]
    data_check_string = "\n".join(pairs).encode("utf-8")

    mac = hmac.new(
        _secret_key(signing_secret),
        msg=data_check_string,
        digestmod=hashlib.sha256,
    )
    calculated_hash = mac.hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InitDataValidationError("hash не совпадает")

    auth_date_raw = data.get("auth_date")
    if auth_date_raw is None:
        raise InitDataValidationError("auth_date отсутствует")
    try:
        auth_ts = int(auth_date_raw)
    except (TypeError, ValueError) as e:
        raise InitDataValidationError("auth_date некорректен") from e

    now = int(time.time())
    if auth_ts > now + 60:
        raise InitDataValidationError("auth_date в будущем")
    if now - auth_ts > max_auth_age_sec:
        raise InitDataValidationError(
            "init_data устарел (закройте и откройте Mini App в Telegram)",
        )

    user_raw = data.get("user")
    if not user_raw:
        raise InitDataValidationError("user отсутствует")

    try:
        user_obj = json.loads(user_raw)
    except json.JSONDecodeError as e:
        raise InitDataValidationError("user не является JSON") from e

    user_id = user_obj.get("id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise InitDataValidationError("user.id некорректен")

    return WebAppUser(id=user_id)
