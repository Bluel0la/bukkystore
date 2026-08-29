from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_catalogue.schemas import (
    AdminCategoryCreate,
    AdminCategoryUpdate,
    AdminProductCreate,
    AdminProductListQuery,
    AdminProductPage,
    AdminProductResponse,
    AdminProductUpdate,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
)
from bukkystore_api.admin_catalogue.service import (
    adjust_stock,
    archive_product,
    create_category,
    create_product,
    get_admin_product,
    list_admin_categories,
    list_admin_products,
    update_category,
    update_product,
)
from bukkystore_api.auth.dependencies import AdminContext, require_admin, require_csrf
from bukkystore_api.catalogue.schemas import CategoryResponse
from bukkystore_api.dependencies import get_session
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin catalogue"],
    responses={
        401: {"model": ErrorResponse, "description": "Administrator sign-in is required."},
        403: {"model": ErrorResponse, "description": "The CSRF token is invalid."},
    },
)
Session = Annotated[AsyncSession, Depends(get_session)]
Authenticated = Annotated[AdminContext, Depends(require_admin)]
MutatingAdmin = Annotated[AdminContext, Depends(require_csrf)]


@router.get("/categories", response_model=list[CategoryResponse])
async def categories(session: Session, _admin: Authenticated) -> list[CategoryResponse]:
    return await list_admin_categories(session)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def category_create(
    payload: AdminCategoryCreate, session: Session, _admin: MutatingAdmin
) -> CategoryResponse:
    return await create_category(session, payload)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def category_update(
    category_id: UUID,
    payload: AdminCategoryUpdate,
    session: Session,
    _admin: MutatingAdmin,
) -> CategoryResponse:
    return await update_category(session, category_id, payload)


@router.get("/products", response_model=AdminProductPage)
async def products(
    session: Session,
    _admin: Authenticated,
    filters: Annotated[AdminProductListQuery, Query()],
) -> AdminProductPage:
    return await list_admin_products(session, filters)


@router.post(
    "/products",
    response_model=AdminProductResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
async def product_create(
    payload: AdminProductCreate, session: Session, admin: MutatingAdmin
) -> AdminProductResponse:
    return await create_product(session, payload, admin.user.id)


@router.get("/products/{product_id}", response_model=AdminProductResponse)
async def product_get(
    product_id: UUID, session: Session, _admin: Authenticated
) -> AdminProductResponse:
    return await get_admin_product(session, product_id)


@router.patch("/products/{product_id}", response_model=AdminProductResponse)
async def product_update(
    product_id: UUID,
    payload: AdminProductUpdate,
    session: Session,
    _admin: MutatingAdmin,
) -> AdminProductResponse:
    return await update_product(session, product_id, payload)


@router.post("/products/{product_id}/archive", response_model=AdminProductResponse)
async def product_archive(
    product_id: UUID, session: Session, _admin: MutatingAdmin
) -> AdminProductResponse:
    return await archive_product(session, product_id)


@router.post("/variants/{variant_id}/stock-adjustments", response_model=StockAdjustmentResponse)
async def stock_adjustment(
    variant_id: UUID,
    payload: StockAdjustmentRequest,
    session: Session,
    admin: MutatingAdmin,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=120, pattern=r"^[A-Za-z0-9:_-]+$"),
    ],
) -> StockAdjustmentResponse:
    return await adjust_stock(
        session,
        variant_id,
        payload,
        idempotency_key=idempotency_key,
        actor_user_id=admin.user.id,
    )
