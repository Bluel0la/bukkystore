from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_settings.schemas import (
    AdminDeliveryAreaCreate,
    AdminDeliveryAreaResponse,
    AdminDeliveryAreaUpdate,
    PublicStoreSettingResponse,
    StoreSettingResponse,
    StoreSettingUpdate,
)
from bukkystore_api.admin_settings.service import (
    create_delivery_area,
    get_public_store_settings,
    get_store_settings,
    list_admin_delivery_areas,
    update_delivery_area,
    update_store_settings,
)
from bukkystore_api.auth.dependencies import AdminContext, require_admin, require_csrf
from bukkystore_api.dependencies import get_session
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin settings"],
    responses={401: {"model": ErrorResponse, "description": "Administrator sign-in is required."}},
)
public_router = APIRouter(prefix="/api/v1", tags=["Storefront settings"])
Session = Annotated[AsyncSession, Depends(get_session)]
Authenticated = Annotated[AdminContext, Depends(require_admin)]
MutatingAdmin = Annotated[AdminContext, Depends(require_csrf)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=120,
        pattern=r"^[A-Za-z0-9:_-]+$",
    ),
]


@public_router.get(
    "/store-settings",
    response_model=PublicStoreSettingResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get public store information",
)
async def public_store_settings(session: Session) -> PublicStoreSettingResponse:
    """Return the safe business details every storefront surface needs."""

    return await get_public_store_settings(session)


@router.get(
    "/store-settings",
    response_model=StoreSettingResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get business settings",
)
async def store_settings(session: Session, _admin: Authenticated) -> StoreSettingResponse:
    """Return the full business configuration for the admin settings screen."""

    return await get_store_settings(session)


@router.patch(
    "/store-settings",
    response_model=StoreSettingResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update business settings",
)
async def store_settings_update(
    payload: StoreSettingUpdate,
    session: Session,
    _admin: MutatingAdmin,
    request: Request,
    idempotency_key: IdempotencyKey,
) -> StoreSettingResponse:
    """Replace business configuration; retried keys replay instead of rewriting."""

    return await update_store_settings(
        session,
        payload,
        idempotency_key=idempotency_key,
        secret=request.app.state.settings.session_secret.get_secret_value(),
    )


@router.get(
    "/delivery-areas",
    response_model=list[AdminDeliveryAreaResponse],
    summary="List delivery areas for administration",
)
async def delivery_areas(
    session: Session, _admin: Authenticated
) -> list[AdminDeliveryAreaResponse]:
    """Return every delivery area, including inactive ones, in display order."""

    return await list_admin_delivery_areas(session)


@router.post(
    "/delivery-areas",
    response_model=AdminDeliveryAreaResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
    summary="Create a delivery area",
)
async def delivery_area_create(
    payload: AdminDeliveryAreaCreate,
    session: Session,
    _admin: MutatingAdmin,
    idempotency_key: IdempotencyKey,
) -> AdminDeliveryAreaResponse:
    """Create a named area with a flat fee; an identical name replays the existing row."""

    return await create_delivery_area(session, payload)


@router.patch(
    "/delivery-areas/{area_id}",
    response_model=AdminDeliveryAreaResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Update a delivery area",
)
async def delivery_area_update(
    area_id: UUID,
    payload: AdminDeliveryAreaUpdate,
    session: Session,
    _admin: MutatingAdmin,
    idempotency_key: IdempotencyKey,
) -> AdminDeliveryAreaResponse:
    """Rename, reprice, reorder, or activate/deactivate one delivery area."""

    return await update_delivery_area(session, area_id, payload)
