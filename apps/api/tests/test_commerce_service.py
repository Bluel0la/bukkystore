from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.catalogue.models import Product, ProductStatus, ProductVariant, VariantStatus
from bukkystore_api.commerce.models import (
    DeliveryArea,
    InventoryReservation,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    ReservationItem,
    ReservationStatus,
)
from bukkystore_api.commerce.payments import (
    FakePaymentProvider,
    PaymentInitializationRequest,
    PaymentInitializationResponse,
    PaymentProviderError,
)
from bukkystore_api.commerce.schemas import CheckoutRequest
from bukkystore_api.commerce.service import (
    create_checkout,
    expire_reservations,
    list_delivery_areas,
)
from bukkystore_api.errors import ApiError


class ScalarItems:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def unique(self) -> ScalarItems:
        return self

    def all(self) -> list[object]:
        return self.items

    def one_or_none(self) -> object | None:
        return self.items[0] if self.items else None


def _area() -> DeliveryArea:
    return DeliveryArea(
        id=uuid4(), name="Lagos Mainland", fee_minor=300_000, currency="NGN", is_active=True
    )


def _variant(*, stock: int = 5, reserved: int = 1) -> ProductVariant:
    product = Product(
        id=uuid4(),
        name="Brown Dress",
        slug="brown-dress",
        description="A dress",
        base_price_minor=1_850_000,
        currency="NGN",
        status=ProductStatus.ACTIVE,
    )
    return ProductVariant(
        id=uuid4(),
        product=product,
        sku="DRESS-BRN-M",
        display_name="Brown / M",
        colour="Brown",
        size="M",
        stock_on_hand=stock,
        reserved_quantity=reserved,
        low_stock_threshold=2,
        status=VariantStatus.ACTIVE,
    )


def _payload(area: DeliveryArea, variant: ProductVariant, *, quantity: int = 2) -> CheckoutRequest:
    return CheckoutRequest.model_validate(
        {
            "customer": {
                "full_name": "Ada Okafor",
                "phone": "08012345678",
                "email": "ada@example.com",
            },
            "delivery": {"area_id": str(area.id), "address": "12 Example Street, Lagos"},
            "items": [{"variant_id": str(variant.id), "quantity": quantity}],
            "attribution": {"source": "instagram", "campaign": "launch"},
        }
    )


def _session(area: DeliveryArea, variants: list[ProductVariant]) -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=area)
    session.scalars = AsyncMock(side_effect=[ScalarItems([]), ScalarItems(list(variants))])
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


async def test_list_delivery_areas_returns_server_fees() -> None:
    area = _area()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([area]))

    result = await list_delivery_areas(session)

    assert result[0].fee_minor == 300_000


async def test_checkout_calculates_totals_reserves_stock_and_initializes_payment() -> None:
    area = _area()
    variant = _variant()
    session = _session(area, [variant])

    response = await create_checkout(
        session,
        _payload(area, variant),
        idempotency_key="checkout-test-key-0001",
        secret="test-secret-value-with-at-least-32-characters",
        reservation_minutes=15,
        provider=FakePaymentProvider("http://localhost:3000"),
    )

    created_order = session.add.call_args.args[0]
    assert isinstance(created_order, Order)
    assert response.summary.subtotal_minor == 3_700_000
    assert response.summary.total_minor == 4_000_000
    assert response.payment_status is PaymentStatus.PENDING
    assert response.idempotent_replay is False
    assert variant.reserved_quantity == 3
    assert created_order.items[0].unit_price_minor == 1_850_000
    assert session.commit.await_count == 2


async def test_checkout_rejects_insufficient_stock_without_persisting() -> None:
    area = _area()
    variant = _variant(stock=2, reserved=1)
    session = _session(area, [variant])

    with pytest.raises(ApiError, match="not enough stock") as error:
        await create_checkout(
            session,
            _payload(area, variant, quantity=2),
            idempotency_key="checkout-test-key-0002",
            secret="test-secret-value-with-at-least-32-characters",
            reservation_minutes=15,
            provider=FakePaymentProvider("http://localhost:3000"),
        )

    assert error.value.status_code == 409
    session.add.assert_not_called()


class FailingProvider:
    name = "fake"

    async def initialize(
        self, _request: PaymentInitializationRequest
    ) -> PaymentInitializationResponse:
        raise PaymentProviderError


async def test_payment_failure_releases_reservation_and_cancels_order() -> None:
    area = _area()
    variant = _variant()
    session = _session(area, [variant])

    with pytest.raises(ApiError) as error:
        await create_checkout(
            session,
            _payload(area, variant),
            idempotency_key="checkout-test-key-0003",
            secret="test-secret-value-with-at-least-32-characters",
            reservation_minutes=15,
            provider=FailingProvider(),
        )

    order = session.add.call_args.args[0]
    assert error.value.status_code == 503
    assert variant.reserved_quantity == 1
    assert order.status is OrderStatus.CANCELLED
    assert order.reservation.status is ReservationStatus.RELEASED
    assert order.payments[0].status is PaymentStatus.FAILED
    assert session.commit.await_count == 2


async def test_identical_idempotent_retry_returns_existing_checkout() -> None:
    area = _area()
    variant = _variant()
    payload = _payload(area, variant)
    first_session = _session(area, [variant])
    first = await create_checkout(
        first_session,
        payload,
        idempotency_key="checkout-test-key-0004",
        secret="test-secret-value-with-at-least-32-characters",
        reservation_minutes=15,
        provider=FakePaymentProvider("http://localhost:3000"),
    )
    order = first_session.add.call_args.args[0]
    replay_session = MagicMock(spec=AsyncSession)
    replay_session.scalars = AsyncMock(return_value=ScalarItems([order]))

    replay = await create_checkout(
        replay_session,
        payload,
        idempotency_key="checkout-test-key-0004",
        secret="test-secret-value-with-at-least-32-characters",
        reservation_minutes=15,
        provider=FakePaymentProvider("http://localhost:3000"),
    )

    assert replay.order_number == first.order_number
    assert replay.order_access_token == first.order_access_token
    assert replay.idempotent_replay is True


async def test_reused_idempotency_key_with_different_request_conflicts() -> None:
    area = _area()
    variant = _variant()
    existing = Order(
        id=uuid4(),
        order_number="BS-20260829-EXISTING",
        idempotency_key_hash="hash",
        request_fingerprint="different",
        access_token_hash="token-hash",
        customer_full_name="Ada Okafor",
        customer_phone="08012345678",
        delivery_area=area,
        delivery_area_name=area.name,
        delivery_address="12 Example Street",
        subtotal_minor=100,
        delivery_fee_minor=20,
        total_minor=120,
        currency="NGN",
        status=OrderStatus.AWAITING_PAYMENT,
    )
    existing.reservation = InventoryReservation(
        status=ReservationStatus.ACTIVE, expires_at=datetime.now(UTC) + timedelta(minutes=15)
    )
    existing.payments.append(
        Payment(
            provider="fake",
            internal_reference="BKS-EXISTING",
            expected_amount_minor=120,
            currency="NGN",
            status=PaymentStatus.PENDING,
            payment_url="http://localhost:3000/pay",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
    )
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([existing]))

    with pytest.raises(ApiError) as error:
        await create_checkout(
            session,
            _payload(area, variant),
            idempotency_key="checkout-test-key-0005",
            secret="test-secret-value-with-at-least-32-characters",
            reservation_minutes=15,
            provider=FakePaymentProvider("http://localhost:3000"),
        )

    assert error.value.code == "idempotency_conflict"


async def test_expired_reservations_release_counters_once() -> None:
    variant = _variant(stock=5, reserved=2)
    expiry_time = datetime.now(UTC)
    reservation = InventoryReservation(
        id=uuid4(), status=ReservationStatus.ACTIVE, expires_at=expiry_time
    )
    reservation.items.append(ReservationItem(variant=variant, variant_id=variant.id, quantity=2))
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(side_effect=[ScalarItems([reservation]), ScalarItems([variant])])
    session.commit = AsyncMock()

    count = await expire_reservations(session, now=expiry_time)

    assert count == 1
    assert variant.reserved_quantity == 0
    assert reservation.status is ReservationStatus.EXPIRED
    session.commit.assert_awaited_once()


async def test_expiry_fails_on_inconsistent_reserved_counter() -> None:
    variant = _variant(stock=5, reserved=0)
    reservation = InventoryReservation(
        id=uuid4(), status=ReservationStatus.ACTIVE, expires_at=datetime.now(UTC)
    )
    reservation.items.append(ReservationItem(variant=variant, variant_id=variant.id, quantity=1))
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(side_effect=[ScalarItems([reservation]), ScalarItems([variant])])

    with pytest.raises(RuntimeError, match="inconsistent"):
        await expire_reservations(session)


async def test_expiry_noops_when_nothing_is_due() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([]))

    assert await expire_reservations(session) == 0
