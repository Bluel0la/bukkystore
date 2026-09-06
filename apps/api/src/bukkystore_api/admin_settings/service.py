from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_settings.models import StoreSetting
from bukkystore_api.admin_settings.schemas import (
    AdminDeliveryAreaCreate,
    AdminDeliveryAreaResponse,
    AdminDeliveryAreaUpdate,
    BusinessHours,
    PublicStoreSettingResponse,
    StoreSettingResponse,
    StoreSettingUpdate,
)
from bukkystore_api.auth.security import hash_token
from bukkystore_api.commerce.models import DeliveryArea
from bukkystore_api.errors import ApiError


def normalize_nigerian_phone(value: str) -> str:
    """Convert a local 0-prefixed number to E.164 so WhatsApp links stay consistent."""

    digits = value.strip()
    if digits.startswith("0"):
        return f"+234{digits[1:]}"
    return digits


def _fingerprint(payload: StoreSettingUpdate) -> str:
    encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _settings_response(row: StoreSetting) -> StoreSettingResponse:
    return StoreSettingResponse(
        id=row.id,
        store_name=row.store_name,
        logo_ref=row.logo_ref,
        whatsapp_number=row.whatsapp_number,
        phone_number=row.phone_number,
        instagram_url=row.instagram_url,
        tiktok_url=row.tiktok_url,
        address=row.address,
        city=row.city,
        currency=row.currency,
        minimum_order_minor=row.minimum_order_minor,
        business_hours=BusinessHours.model_validate(row.business_hours),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _public_response(row: StoreSetting) -> PublicStoreSettingResponse:
    return PublicStoreSettingResponse(
        store_name=row.store_name,
        logo_ref=row.logo_ref,
        whatsapp_number=row.whatsapp_number,
        phone_number=row.phone_number,
        instagram_url=row.instagram_url,
        tiktok_url=row.tiktok_url,
        address=row.address,
        city=row.city,
        currency=row.currency,
        minimum_order_minor=row.minimum_order_minor,
        business_hours=BusinessHours.model_validate(row.business_hours),
    )


def _area_response(area: DeliveryArea) -> AdminDeliveryAreaResponse:
    return AdminDeliveryAreaResponse(
        id=area.id,
        name=area.name,
        fee_minor=area.fee_minor,
        currency=area.currency,
        display_position=area.display_position,
        is_active=area.is_active,
    )


async def get_store_settings(session: AsyncSession) -> StoreSettingResponse:
    row = await session.scalar(select(StoreSetting))
    if row is None:
        raise ApiError(404, "settings_not_configured", "The store settings are not configured.")
    return _settings_response(row)


async def get_public_store_settings(session: AsyncSession) -> PublicStoreSettingResponse:
    row = await session.scalar(select(StoreSetting))
    if row is None:
        raise ApiError(404, "settings_not_configured", "The store settings are not configured.")
    return _public_response(row)


async def update_store_settings(
    session: AsyncSession,
    payload: StoreSettingUpdate,
    *,
    idempotency_key: str,
    secret: str,
) -> StoreSettingResponse:
    """Apply business configuration; a retried key replays instead of rewriting."""

    row = await session.scalar(select(StoreSetting))
    if row is None:
        raise ApiError(404, "settings_not_configured", "The store settings are not configured.")
    key_hash = hash_token(idempotency_key, secret)
    fingerprint = _fingerprint(payload)
    if row.last_idempotency_key_hash == key_hash:
        if row.last_request_fingerprint != fingerprint:
            raise ApiError(409, "idempotency_conflict", "The idempotency key was already used.")
        return _settings_response(row)
    row.store_name = payload.store_name
    row.logo_ref = payload.logo_ref
    row.whatsapp_number = normalize_nigerian_phone(payload.whatsapp_number)
    row.phone_number = normalize_nigerian_phone(payload.phone_number)
    row.instagram_url = payload.instagram_url
    row.tiktok_url = payload.tiktok_url
    row.address = payload.address
    row.city = payload.city
    row.currency = payload.currency
    row.minimum_order_minor = payload.minimum_order_minor
    row.business_hours = payload.business_hours.model_dump(mode="json")
    row.last_idempotency_key_hash = key_hash
    row.last_request_fingerprint = fingerprint
    await session.commit()
    return _settings_response(row)


async def list_admin_delivery_areas(session: AsyncSession) -> list[AdminDeliveryAreaResponse]:
    areas = (
        await session.scalars(
            select(DeliveryArea).order_by(DeliveryArea.display_position, DeliveryArea.name)
        )
    ).all()
    return [_area_response(area) for area in areas]


async def create_delivery_area(
    session: AsyncSession, payload: AdminDeliveryAreaCreate
) -> AdminDeliveryAreaResponse:
    """Create an area; an identical name replays the existing row instead of duplicating."""

    existing = await session.scalar(
        select(DeliveryArea).where(DeliveryArea.name == payload.name.strip())
    )
    if existing is not None:
        if (
            existing.fee_minor != payload.fee_minor
            or existing.currency != payload.currency
            or existing.display_position != payload.display_position
            or existing.is_active != payload.is_active
        ):
            raise ApiError(
                409, "delivery_area_exists", "A delivery area with this name already exists."
            )
        return _area_response(existing)
    area = DeliveryArea(
        name=payload.name.strip(),
        fee_minor=payload.fee_minor,
        currency=payload.currency,
        display_position=payload.display_position,
        is_active=payload.is_active,
    )
    session.add(area)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(
            409, "delivery_area_exists", "A delivery area with this name already exists."
        ) from exc
    return _area_response(area)


async def update_delivery_area(
    session: AsyncSession, area_id: UUID, payload: AdminDeliveryAreaUpdate
) -> AdminDeliveryAreaResponse:
    area = await session.get(DeliveryArea, area_id)
    if area is None:
        raise ApiError(404, "delivery_area_not_found", "The delivery area was not found.")
    if payload.name is not None:
        area.name = payload.name.strip()
    if payload.fee_minor is not None:
        area.fee_minor = payload.fee_minor
    if payload.currency is not None:
        area.currency = payload.currency
    if payload.display_position is not None:
        area.display_position = payload.display_position
    if payload.is_active is not None:
        area.is_active = payload.is_active
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(
            409, "delivery_area_exists", "A delivery area with this name already exists."
        ) from exc
    return _area_response(area)
