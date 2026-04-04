"""Тесты чистой логики статусов заказа (без БД и Telegram)."""

from __future__ import annotations

import unittest

from fastapi import HTTPException

from tg_mini_app.api.customer_identity import assert_cart_mutation_allowed
from tg_mini_app.order_flow import (
    MSG_NOT_OPERATOR,
    MSG_PAYMENT_ALREADY_DONE,
    MSG_STALE_ORDER,
    OrderStatus,
    require_active_for_ship,
    require_awaiting_payment,
    require_operator_identity,
    require_pending_customer_change,
    require_pending_operator_for_action,
    require_pending_operator_for_cancel,
)


class TestOperatorIdentity(unittest.TestCase):
    def test_no_config_allows_anyone(self) -> None:
        self.assertIsNone(require_operator_identity(1, None))

    def test_configured_match(self) -> None:
        self.assertIsNone(require_operator_identity(42, 42))

    def test_configured_mismatch(self) -> None:
        self.assertEqual(
            require_operator_identity(1, 999),
            MSG_NOT_OPERATOR,
        )


class TestPendingOperator(unittest.TestCase):
    def test_ok(self) -> None:
        self.assertIsNone(
            require_pending_operator_for_action(OrderStatus.PENDING_OPERATOR),
        )

    def test_stale(self) -> None:
        for s in (
            OrderStatus.AWAITING_PAYMENT,
            OrderStatus.ACTIVE,
            OrderStatus.REJECTED_BY_OPERATOR,
        ):
            with self.subTest(status=s):
                self.assertEqual(
                    require_pending_operator_for_action(s),
                    MSG_STALE_ORDER,
                )


class TestCustomerChange(unittest.TestCase):
    def test_ok(self) -> None:
        self.assertIsNone(
            require_pending_customer_change(
                OrderStatus.PENDING_CUSTOMER_CHANGE_ACCEPT,
            ),
        )

    def test_stale(self) -> None:
        self.assertEqual(
            require_pending_customer_change(OrderStatus.AWAITING_PAYMENT),
            MSG_STALE_ORDER,
        )


class TestCancelByCustomer(unittest.TestCase):
    def test_ok(self) -> None:
        self.assertIsNone(
            require_pending_operator_for_cancel(OrderStatus.PENDING_OPERATOR),
        )

    def test_stale(self) -> None:
        self.assertEqual(
            require_pending_operator_for_cancel(OrderStatus.AWAITING_PAYMENT),
            MSG_STALE_ORDER,
        )


class TestShip(unittest.TestCase):
    def test_ok_active(self) -> None:
        self.assertIsNone(require_active_for_ship(OrderStatus.ACTIVE))

    def test_stale(self) -> None:
        self.assertEqual(
            require_active_for_ship(OrderStatus.PENDING_OPERATOR),
            MSG_STALE_ORDER,
        )


class TestCartOwner(unittest.TestCase):
    def test_no_owner(self) -> None:
        assert_cart_mutation_allowed(None, 1)

    def test_match(self) -> None:
        assert_cart_mutation_allowed(5, 5)

    def test_mismatch(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            assert_cart_mutation_allowed(5, 9)
        self.assertEqual(ctx.exception.status_code, 403)


class TestPayment(unittest.TestCase):
    def test_ok(self) -> None:
        self.assertIsNone(
            require_awaiting_payment(OrderStatus.AWAITING_PAYMENT),
        )

    def test_already_active(self) -> None:
        self.assertEqual(
            require_awaiting_payment(OrderStatus.ACTIVE),
            MSG_PAYMENT_ALREADY_DONE,
        )

    def test_wrong_state(self) -> None:
        self.assertEqual(
            require_awaiting_payment(OrderStatus.PENDING_OPERATOR),
            MSG_STALE_ORDER,
        )


if __name__ == "__main__":
    unittest.main()
