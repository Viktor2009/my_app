"""Подпись cookie-сессии панели оператора."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tg_mini_app.api.operator_panel import (
    _make_panel_session_cookie,
    _panel_session_cookie_ok,
)


class TestOperatorPanelCookie(unittest.TestCase):
    def test_valid_within_ttl(self) -> None:
        with patch("tg_mini_app.api.operator_panel.time") as mock_time:
            mock_time.time.return_value = 1_000_000.0
            raw = _make_panel_session_cookie("my-secret", ttl_sec=3600)
        with patch("tg_mini_app.api.operator_panel.time") as mock_time:
            mock_time.time.return_value = 1_000_100.0
            self.assertTrue(_panel_session_cookie_ok(raw, "my-secret"))

    def test_wrong_secret(self) -> None:
        with patch("tg_mini_app.api.operator_panel.time") as mock_time:
            mock_time.time.return_value = 1_000_000.0
            raw = _make_panel_session_cookie("a", ttl_sec=3600)
        self.assertFalse(_panel_session_cookie_ok(raw, "b"))

    def test_expired(self) -> None:
        with patch("tg_mini_app.api.operator_panel.time") as mock_time:
            mock_time.time.return_value = 1_000_000.0
            raw = _make_panel_session_cookie("s", ttl_sec=10)
        with patch("tg_mini_app.api.operator_panel.time") as mock_time:
            mock_time.time.return_value = 1_000_100.0
            self.assertFalse(_panel_session_cookie_ok(raw, "s"))

    def test_malformed(self) -> None:
        self.assertFalse(_panel_session_cookie_ok("not-a-cookie", "s"))
        self.assertFalse(_panel_session_cookie_ok("abc", "s"))


if __name__ == "__main__":
    unittest.main()
