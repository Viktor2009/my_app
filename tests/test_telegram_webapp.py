"""Проверка разбора и подписи Telegram WebApp initData."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from tg_mini_app.api.telegram_webapp import (
    InitDataValidationError,
    validate_init_data_and_get_user_id,
)


def _make_init_data(
    *,
    user_id: int,
    signing_secret: str,
    auth_date: int | None = None,
) -> str:
    if auth_date is None:
        auth_date = int(time.time())
    user_json = json.dumps({"id": user_id, "first_name": "T"}, separators=(",", ":"))
    data: dict[str, str] = {
        "user": user_json,
        "auth_date": str(auth_date),
        "query_id": "test",
    }
    pairs = sorted(data.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in pairs).encode("utf-8")
    sk = hmac.new(b"WebAppData", signing_secret.encode("utf-8"), hashlib.sha256).digest()
    signature = hmac.new(sk, data_check_string, hashlib.sha256).hexdigest()
    data["hash"] = signature
    return urlencode(data)


class TestTelegramWebAppInitData(unittest.TestCase):
    def test_accepts_valid_signature(self) -> None:
        raw = _make_init_data(user_id=42, signing_secret="123:abcd")
        u = validate_init_data_and_get_user_id(
            raw,
            signing_secret="123:abcd",
            max_auth_age_sec=3600,
        )
        self.assertEqual(u.id, 42)

    def test_rejects_wrong_secret(self) -> None:
        raw = _make_init_data(user_id=42, signing_secret="123:abcd")
        with self.assertRaises(InitDataValidationError):
            validate_init_data_and_get_user_id(raw, signing_secret="other")

    def test_rejects_stale_auth_date(self) -> None:
        old = int(time.time()) - 10_000
        raw = _make_init_data(
            user_id=7,
            signing_secret="tok",
            auth_date=old,
        )
        with self.assertRaises(InitDataValidationError) as ctx:
            validate_init_data_and_get_user_id(
                raw,
                signing_secret="tok",
                max_auth_age_sec=1000,
            )
        self.assertIn("устарел", str(ctx.exception))


class TestTelegramWebAppAuthDateCheck(unittest.TestCase):
    def test_future_auth_date(self) -> None:
        raw = _make_init_data(user_id=1, signing_secret="s", auth_date=2_000_000_000)
        with patch("tg_mini_app.api.telegram_webapp.time") as mock_time:
            mock_time.time.return_value = 1_000
            with self.assertRaises(InitDataValidationError) as ctx:
                validate_init_data_and_get_user_id(raw, signing_secret="s")
        self.assertIn("будущем", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
