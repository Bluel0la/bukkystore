"""Regression tests for locked-query shapes.

PostgreSQL rejects bare FOR UPDATE over the outer joins that joinedload
produces, which surfaces as a 500 only against a real database — mocks never
execute SQL. These tests drive the real service functions with capturing
mock sessions, compile the captured statements with the PostgreSQL dialect,
and assert every locked statement carries FOR UPDATE with no JOIN.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import Select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_catalogue.service import archive_product, bulk_set_archived
from bukkystore_api.admin_orders.schemas import RefundCompletionRequest
from bukkystore_api.admin_orders.service import _locked_order, complete_refund
from bukkystore_api.catalogue.models import (
    Category,
    Product,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.commerce.models import DeliveryArea, Order, Payment
from bukkystore_api.commerce.payments import FakePaymentProvider
from bukkystore_api.commerce.schemas import CheckoutRequest
from bukkystore_api.commerce.service import _locked_payment, create_checkout
from bukkystore_api.errors import ApiError


class Rows:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def unique(self) -> Rows:
        return self

    def all(self) -> list[Any]:
        return self.items

    def one_or_none(self) -> Any | None:
        return self.items[0] if self.items else None


def _compiled(stmt: Select[Any]) -> str:
    return str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    ).upper()


def _assert_lock_without_join(stmt: Select[Any]) -> None:
    sql = _compiled(stmt)
    assert "FOR UPDATE" in sql
    assert "JOIN" not in sql


def _product() -> Product:
    now = datetime.now(UTC)
    category = Category(
        id=uuid4(), name="Dresses", slug="dresses", display_position=0, is_active=True
    )
    product = Product(
        id=uuid4(),
        category=category,
        name="Brown Dress",
        slug="brown-dress",
        description="A dress",
        base_price_minor=1_850_000,
        compare_at_price_minor=None,
        currency="NGN",
        status=ProductStatus.ACTIVE,
        featured=False,
        created_at=now,
        updated_at=now,
    )
    product.variants.append(
        ProductVariant(
            id=uuid4(),
            sku="DRESS-BRN-M",
            display_name="Brown / M",
            colour="Brown",
            size="M",
            price_override_minor=None,
            stock_on_hand=4,
            reserved_quantity=0,
            low_stock_threshold=2,
            status=VariantStatus.ACTIVE,
        )
    )
    return product


async def test_archive_lock_select_has_no_join() -> None:
    product = _product()
    captured: list[Select[Any]] = []
    session = MagicMock(spec=AsyncSession)

    async def scalars(stmt: Select[Any]) -> Rows:
        captured.append(stmt)
        return Rows([product])

    session.scalars = scalars
    session.commit = AsyncMock()

    archived = await archive_product(session, product.id)

    assert archived.status is ProductStatus.ARCHIVED
    assert len(captured) == 1
    _assert_lock_without_join(captured[0])


async def test_bulk_archive_lock_select_has_no_join() -> None:
    first, second = _product(), _product()
    captured: list[Select[Any]] = []
    session = MagicMock(spec=AsyncSession)

    async def scalars(stmt: Select[Any]) -> Rows:
        captured.append(stmt)
        return Rows([first, second])

    session.scalars = scalars
    session.commit = AsyncMock()

    updated = await bulk_set_archived(session, [first.id, second.id], archived=True)

    assert updated == sorted([first.id, second.id])
    assert len(captured) == 1
    _assert_lock_without_join(captured[0])


async def test_checkout_variant_lock_select_has_no_join() -> None:
    area = DeliveryArea(
        id=uuid4(), name="Lagos Mainland", fee_minor=300_000, currency="NGN", is_active=True
    )
    now = datetime.now(UTC)
    variant = ProductVariant(
        id=uuid4(),
        sku="DRESS-BRN-M",
        display_name="Brown / M",
        colour="Brown",
        size="M",
        price_override_minor=None,
        stock_on_hand=5,
        reserved_quantity=0,
        low_stock_threshold=2,
        status=VariantStatus.ACTIVE,
    )
    variant.product = Product(
        id=uuid4(),
        name="Brown Dress",
        slug="brown-dress",
        description="A dress",
        base_price_minor=1_850_000,
        currency="NGN",
        status=ProductStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    captured: list[Select[Any]] = []
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=area)

    async def scalars(stmt: Select[Any]) -> Rows:
        captured.append(stmt)
        # First call checks for an idempotent retry (none); second locks variants.
        return Rows([]) if len(captured) == 1 else Rows([variant])

    session.scalars = scalars
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    payload = CheckoutRequest.model_validate(
        {
            "customer": {"full_name": "Ada Okafor", "phone": "08012345678"},
            "delivery": {"area_id": str(area.id), "address": "12 Example Street, Lagos"},
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        }
    )

    await create_checkout(
        session,
        payload,
        idempotency_key="lock-shape-key-0001",
        secret="test-secret-value-with-at-least-32-characters",
        reservation_minutes=15,
        provider=FakePaymentProvider("http://localhost:3000"),
    )

    assert len(captured) == 2
    _assert_lock_without_join(captured[1])


async def test_locked_payment_select_has_no_join() -> None:
    captured: list[Select[Any]] = []
    session = MagicMock(spec=AsyncSession)

    async def scalars(stmt: Select[Any]) -> Rows:
        captured.append(stmt)
        return Rows([Payment()])

    session.scalars = scalars

    payment = await _locked_payment(session, "internal-ref-0001")

    assert payment is not None
    assert len(captured) == 1
    _assert_lock_without_join(captured[0])


async def test_locked_order_select_has_no_join() -> None:
    captured: list[Select[Any]] = []
    session = MagicMock(spec=AsyncSession)

    async def scalars(stmt: Select[Any]) -> Rows:
        captured.append(stmt)
        return Rows([Order()])

    session.scalars = scalars

    order = await _locked_order(session, uuid4())

    assert order is not None
    assert len(captured) == 1
    _assert_lock_without_join(captured[0])


async def test_refund_lock_select_has_no_join() -> None:
    captured: list[Select[Any]] = []
    session = MagicMock(spec=AsyncSession)

    async def scalar(stmt: Select[Any]) -> None:
        captured.append(stmt)
        return None

    session.scalar = scalar

    with pytest.raises(ApiError) as error:
        await complete_refund(
            session,
            uuid4(),
            RefundCompletionRequest(),
            actor_user_id=uuid4(),
            idempotency_key="lock-shape-key-0002",
            secret="test-secret-value-with-at-least-32-characters",
        )

    assert error.value.code == "refund_not_found"
    assert len(captured) == 1
    _assert_lock_without_join(captured[0])
