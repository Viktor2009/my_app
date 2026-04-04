from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tg_mini_app.api.customer_identity import (
    assert_cart_mutation_allowed,
    resolve_customer_tg_id,
)
from tg_mini_app.api.deps import get_db_session
from tg_mini_app.api.schemas import OrderCreateRequest, OrderResponse
from tg_mini_app.db import models
from tg_mini_app.order_flow import (
    OrderStatus,
    require_pending_operator_for_cancel,
    unlock_cart_if_locked,
)
from tg_mini_app.settings import get_settings

router = APIRouter(prefix="/orders", tags=["orders"])


async def _load_cart_for_order(session: AsyncSession, cart_id: str) -> models.Cart:
    cart = (
        await session.execute(
            select(models.Cart)
            .where(models.Cart.id == cart_id)
            .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))
        )
    ).scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=404, detail="Корзина не найдена")
    return cart


def _calc_total(cart: models.Cart) -> Decimal:
    total = Decimal("0")
    for it in cart.items:
        total += Decimal(it.price_snapshot) * it.qty
    return total


def _order_to_response(order: models.Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        cart_id=order.cart_id,
        customer_tg_id=order.customer_tg_id,
        address=order.address,
        delivery_time=order.delivery_time,
        customer_comment=order.customer_comment,
        status=order.status,
        payment_type=order.payment_type,
        total_amount=Decimal(order.total_amount),
    )


async def _notify_operator_if_possible(
    request: Request,
    order: models.Order,
    cart: models.Cart,
) -> None:
    bot: Bot | None = getattr(request.app.state, "bot", None)
    if bot is None:
        return

    settings = get_settings()
    operator_chat_id = settings.operator_chat_id
    operator_username = settings.operator_username.strip()
    if operator_chat_id is None and not operator_username:
        return

    items_lines: list[str] = []
    for it in cart.items:
        items_lines.append(f"- {it.product.name} × {it.qty}")

    text = (
        "Новый заказ на согласование\n\n"
        f"Заказ #{order.id}\n"
        f"Адрес: {order.address}\n"
        f"Время: {order.delivery_time}\n"
        f"Сумма: {order.total_amount} ₽\n\n"
        "Состав:\n"
        + "\n".join(items_lines)
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"order:{order.id}:approve"),
                InlineKeyboardButton(text="Нет", callback_data=f"order:{order.id}:reject"),
                InlineKeyboardButton(text="Изменить", callback_data=f"order:{order.id}:change"),
            ]
        ]
    )

    chat_id: int | str = operator_chat_id if operator_chat_id is not None else operator_username
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)
    except Exception as e:
        # Не прерываем создание заказа, но фиксируем ошибку для диагностики.
        # В проде здесь будет нормальный логгер.
        meta = dict(order.meta)
        meta["operator_notify_error"] = repr(e)
        order.meta = meta
        request.state._operator_notify_error = repr(e)


async def _notify_operator_text(request: Request, text: str) -> None:
    bot: Bot | None = getattr(request.app.state, "bot", None)
    if bot is None:
        return
    settings = get_settings()
    operator_chat_id = settings.operator_chat_id
    operator_username = settings.operator_username.strip()
    if operator_chat_id is None and not operator_username:
        return
    chat_id: int | str = operator_chat_id if operator_chat_id is not None else operator_username
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        pass


@router.post("", response_model=OrderResponse)
async def create_order(
    payload: OrderCreateRequest,
    request: Request,
    x_telegram_init_data: Annotated[
        str | None,
        Header(alias="X-Telegram-Init-Data"),
    ] = None,
    session: AsyncSession = Depends(get_db_session),
) -> OrderResponse:
    cart = await _load_cart_for_order(session, payload.cart_id)
    if cart.status != "open":
        raise HTTPException(status_code=409, detail="Корзина закрыта")
    if not cart.items:
        raise HTTPException(status_code=409, detail="Корзина пуста")

    settings = get_settings()
    raw_init = (
        (x_telegram_init_data or payload.init_data or "").strip() or None
    )
    customer_tg_id = resolve_customer_tg_id(
        raw_init,
        payload.customer_tg_id,
        settings=settings,
    )
    assert_cart_mutation_allowed(cart.owner_tg_id, customer_tg_id)

    total = _calc_total(cart)
    meta_items: list[dict[str, Any]] = [
        {
            "product_id": it.product_id,
            "name": it.product.name,
            "qty": it.qty,
            "price_snapshot": str(it.price_snapshot),
        }
        for it in cart.items
    ]

    order = models.Order(
        cart_id=cart.id,
        customer_tg_id=customer_tg_id,
        address=payload.address,
        delivery_time=payload.delivery_time,
        customer_comment=payload.customer_comment,
        status=OrderStatus.PENDING_OPERATOR,
        payment_type="",
        total_amount=total,
        meta={"items": meta_items},
    )
    session.add(order)

    cart.status = "locked"
    await session.commit()
    await session.refresh(order)

    await _notify_operator_if_possible(request, order, cart)
    await session.commit()
    return _order_to_response(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_for_customer(
    order_id: int,
    session: AsyncSession = Depends(get_db_session),
    init_data: Annotated[str | None, Query()] = None,
    x_telegram_init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
    customer_tg_id: Annotated[int | None, Query()] = None,
) -> OrderResponse:
    """
    Статус заказа для клиента Mini App.
    init_data можно передать в query или в заголовке (длинные строки — лучше заголовок).
    """
    raw_init = (x_telegram_init_data or init_data or "").strip() or None
    settings = get_settings()
    tg_id = resolve_customer_tg_id(raw_init, customer_tg_id, settings=settings)

    order = (
        await session.execute(select(models.Order).where(models.Order.id == order_id))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_tg_id != tg_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

    return _order_to_response(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order_by_customer(
    order_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    init_data: Annotated[str | None, Query()] = None,
    x_telegram_init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
    customer_tg_id: Annotated[int | None, Query()] = None,
) -> OrderResponse:
    """Отмена до ответа оператора (статус pending_operator)."""
    raw_init = (x_telegram_init_data or init_data or "").strip() or None
    settings = get_settings()
    tg_id = resolve_customer_tg_id(raw_init, customer_tg_id, settings=settings)

    order = (
        await session.execute(select(models.Order).where(models.Order.id == order_id))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_tg_id != tg_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

    cancel_err = require_pending_operator_for_cancel(order.status)
    if cancel_err is not None:
        raise HTTPException(status_code=409, detail=cancel_err)

    order.status = OrderStatus.CANCELLED_BY_CUSTOMER
    await unlock_cart_if_locked(session, order.cart_id)
    await session.commit()

    await _notify_operator_text(
        request,
        f"Клиент отменил заказ #{order.id} до согласования.",
    )
    return _order_to_response(order)

