from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from bukkystore_api.auth.security import hash_token
from bukkystore_api.catalogue.models import ProductStatus, ProductVariant, VariantStatus
from bukkystore_api.commerce.models import (
    DeliveryArea,
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    ReservationItem,
    ReservationStatus,
)
from bukkystore_api.commerce.payments import (
    PaymentInitializationRequest,
    PaymentInitializationResponse,
    PaymentProvider,
    PaymentProviderError,
)
from bukkystore_api.commerce.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    CheckoutSummary,
    DeliveryAreaResponse,
)
from bukkystore_api.errors import ApiError

logger = logging.getLogger(__name__)


def _fingerprint(payload: CheckoutRequest) -> str:
    encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _order_access_token(order_id: UUID, secret: str) -> str:
    return hash_token(f"order-access:{order_id}", secret)


def _response(order: Order, payment: Payment, *, secret: str, replay: bool) -> CheckoutResponse:
    if order.reservation is None or payment.payment_url is None:
        raise ApiError(409, "checkout_not_ready", "The checkout is not ready for payment.")
    return CheckoutResponse(
        order_number=order.order_number,
        order_status=order.status,
        payment_status=payment.status,
        reservation_expires_at=order.reservation.expires_at,
        summary=CheckoutSummary(
            subtotal_minor=order.subtotal_minor,
            delivery_fee_minor=order.delivery_fee_minor,
            total_minor=order.total_minor,
            currency=order.currency,
        ),
        payment_url=payment.payment_url,
        order_access_token=_order_access_token(order.id, secret),
        idempotent_replay=replay,
    )


async def list_delivery_areas(session: AsyncSession) -> list[DeliveryAreaResponse]:
    areas = (
        await session.scalars(
            select(DeliveryArea)
            .where(DeliveryArea.is_active.is_(True))
            .order_by(DeliveryArea.display_position, DeliveryArea.name)
        )
    ).all()
    return [
        DeliveryAreaResponse(
            id=area.id, name=area.name, fee_minor=area.fee_minor, currency=area.currency
        )
        for area in areas
    ]


async def _existing_order(session: AsyncSession, key_hash: str) -> Order | None:
    return (
        (
            await session.scalars(
                select(Order)
                .where(Order.idempotency_key_hash == key_hash)
                .options(joinedload(Order.reservation), selectinload(Order.payments))
            )
        )
        .unique()
        .one_or_none()
    )


async def create_checkout(
    session: AsyncSession,
    payload: CheckoutRequest,
    *,
    idempotency_key: str,
    secret: str,
    reservation_minutes: int,
    provider: PaymentProvider,
) -> CheckoutResponse:
    key_hash = hash_token(idempotency_key, secret)
    request_fingerprint = _fingerprint(payload)
    existing = await _existing_order(session, key_hash)
    if existing is not None:
        if existing.request_fingerprint != request_fingerprint:
            raise ApiError(409, "idempotency_conflict", "The idempotency key was already used.")
        payment = existing.payments[-1]
        if payment.status is PaymentStatus.PENDING and payment.payment_url is not None:
            return _response(existing, payment, secret=secret, replay=True)
        raise ApiError(409, "checkout_not_payable", "This checkout can no longer be paid.")

    area = await session.get(DeliveryArea, payload.delivery.area_id)
    if area is None or not area.is_active:
        raise ApiError(404, "delivery_area_not_found", "The delivery area is unavailable.")

    requested = {item.variant_id: item.quantity for item in payload.items}
    variants = list(
        (
            await session.scalars(
                select(ProductVariant)
                .where(ProductVariant.id.in_(sorted(requested)))
                .order_by(ProductVariant.id)
                .with_for_update()
                .options(joinedload(ProductVariant.product))
            )
        ).all()
    )
    if len(variants) != len(requested):
        raise ApiError(404, "variant_not_found", "One or more product options are unavailable.")
    if any(
        variant.status is not VariantStatus.ACTIVE
        or variant.product.status is not ProductStatus.ACTIVE
        for variant in variants
    ):
        raise ApiError(409, "variant_unavailable", "One or more product options are unavailable.")

    for variant in variants:
        if requested[variant.id] > variant.available_quantity:
            raise ApiError(
                409,
                "insufficient_stock",
                f"There is not enough stock for {variant.product.name} — {variant.display_name}.",
            )
        if variant.product.currency != area.currency:
            raise ApiError(409, "currency_mismatch", "The checkout currency is inconsistent.")

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=reservation_minutes)
    order_id = uuid4()
    access_token = _order_access_token(order_id, secret)
    subtotal = sum(variant.effective_price_minor * requested[variant.id] for variant in variants)
    order = Order(
        id=order_id,
        order_number=f"BS-{now:%Y%m%d}-{secrets.token_hex(4).upper()}",
        idempotency_key_hash=key_hash,
        request_fingerprint=request_fingerprint,
        access_token_hash=hash_token(access_token, secret),
        customer_full_name=payload.customer.full_name,
        customer_phone=payload.customer.phone,
        customer_email=payload.customer.email,
        delivery_area=area,
        delivery_area_name=area.name,
        delivery_address=payload.delivery.address,
        delivery_directions=payload.delivery.directions,
        subtotal_minor=subtotal,
        delivery_fee_minor=area.fee_minor,
        total_minor=subtotal + area.fee_minor,
        currency=area.currency,
        attribution_source=payload.attribution.source if payload.attribution else None,
        attribution_campaign=payload.attribution.campaign if payload.attribution else None,
        status=OrderStatus.AWAITING_PAYMENT,
    )
    reservation = InventoryReservation(
        id=uuid4(), order=order, status=ReservationStatus.ACTIVE, expires_at=expires_at
    )
    for variant in variants:
        quantity = requested[variant.id]
        unit_price = variant.effective_price_minor
        order.items.append(
            OrderItem(
                product=variant.product,
                variant=variant,
                product_name=variant.product.name,
                variant_name=variant.display_name,
                sku=variant.sku,
                unit_price_minor=unit_price,
                quantity=quantity,
                line_subtotal_minor=unit_price * quantity,
            )
        )
        reservation.items.append(ReservationItem(variant=variant, quantity=quantity))
        variant.reserved_quantity += quantity

    payment = Payment(
        order=order,
        provider=provider.name,
        internal_reference=f"BKS-{order_id.hex.upper()}",
        expected_amount_minor=order.total_minor,
        currency=order.currency,
        status=PaymentStatus.INITIALIZING,
        expires_at=expires_at,
    )
    session.add(order)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raced = await _existing_order(session, key_hash)
        if raced is not None and raced.request_fingerprint == request_fingerprint:
            raced_payment = raced.payments[-1]
            if raced_payment.status is PaymentStatus.PENDING and raced_payment.payment_url:
                return _response(raced, raced_payment, secret=secret, replay=True)
        raise ApiError(409, "checkout_conflict", "The checkout could not be created.") from exc

    logger.info(
        "checkout_calculated",
        extra={
            "order_id": str(order.id),
            "calculated_at": now.isoformat(),
            "subtotal_minor": subtotal,
            "delivery_fee_minor": area.fee_minor,
            "status": order.status.value,
        },
    )
    try:
        initialized = await provider.initialize(
            PaymentInitializationRequest(
                reference=payment.internal_reference,
                amount_minor=payment.expected_amount_minor,
                currency=payment.currency,
                customer_email=order.customer_email,
                customer_phone=order.customer_phone,
                order_number=order.order_number,
            )
        )
        if not isinstance(initialized, PaymentInitializationResponse):
            raise PaymentProviderError
    except (PaymentProviderError, TimeoutError, OSError) as exc:
        for variant in variants:
            variant.reserved_quantity -= requested[variant.id]
        reservation.status = ReservationStatus.RELEASED
        reservation.released_at = datetime.now(UTC)
        payment.status = PaymentStatus.FAILED
        payment.failure_code = "initialization_failed"
        order.status = OrderStatus.CANCELLED
        await session.commit()
        logger.warning(
            "payment_initialization_failed",
            extra={"order_id": str(order.id), "status": payment.status.value},
        )
        raise ApiError(
            503, "payment_unavailable", "Payment could not be started. Please try again."
        ) from exc

    payment.provider_reference = initialized.provider_reference
    payment.payment_url = str(initialized.payment_url)
    payment.status = PaymentStatus.PENDING
    await session.commit()
    logger.info(
        "payment_status_changed",
        extra={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "changed_at": datetime.now(UTC).isoformat(),
        },
    )
    return _response(order, payment, secret=secret, replay=False)


async def expire_reservations(
    session: AsyncSession, *, now: datetime | None = None, batch_size: int = 100
) -> int:
    expiry_time = now or datetime.now(UTC)
    reservations = list(
        (
            await session.scalars(
                select(InventoryReservation)
                .where(
                    InventoryReservation.status == ReservationStatus.ACTIVE,
                    InventoryReservation.expires_at <= expiry_time,
                )
                .order_by(InventoryReservation.expires_at, InventoryReservation.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
                .options(selectinload(InventoryReservation.items))
            )
        )
        .unique()
        .all()
    )
    if not reservations:
        return 0
    variant_ids = sorted(
        {item.variant_id for reservation in reservations for item in reservation.items}
    )
    locked_variants = {
        variant.id: variant
        for variant in (
            await session.scalars(
                select(ProductVariant)
                .where(ProductVariant.id.in_(variant_ids))
                .order_by(ProductVariant.id)
                .with_for_update()
            )
        ).all()
    }
    for reservation in reservations:
        for item in reservation.items:
            variant = locked_variants.get(item.variant_id)
            if variant is None or variant.reserved_quantity < item.quantity:
                raise RuntimeError("Reservation counters are inconsistent")
            variant.reserved_quantity -= item.quantity
        reservation.status = ReservationStatus.EXPIRED
        reservation.released_at = expiry_time
        logger.info(
            "reservation_status_changed",
            extra={
                "reservation_id": str(reservation.id),
                "status": reservation.status.value,
                "expired_at": expiry_time.isoformat(),
                "trigger": "scheduled_expiry",
            },
        )
    if reservations:
        await session.commit()
    return len(reservations)
