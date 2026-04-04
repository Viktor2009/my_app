from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class CartCreateRequest(BaseModel):
    owner_tg_id: int | None = None


class CartItemChangeRequest(BaseModel):
    product_id: int = Field(ge=1)
    qty_delta: int = Field(ge=-100, le=100)
    init_data: str | None = None
    customer_tg_id: int | None = None


class CartItemResponse(BaseModel):
    product_id: int
    name: str
    qty: int
    price: Decimal
    subtotal: Decimal


class CartResponse(BaseModel):
    id: str
    shared_key: str
    status: str
    items: list[CartItemResponse]
    total: Decimal


class ShareResponse(BaseModel):
    shared_key: str


class OrderCreateRequest(BaseModel):
    cart_id: str
    init_data: str | None = None
    customer_tg_id: int | None = None
    address: str = Field(min_length=3, max_length=512)
    delivery_time: str = Field(min_length=2, max_length=64)
    customer_comment: str = Field(default="", max_length=512)


class OrderResponse(BaseModel):
    id: int
    cart_id: str
    customer_tg_id: int
    address: str
    delivery_time: str
    customer_comment: str
    status: str
    payment_type: str
    total_amount: Decimal

