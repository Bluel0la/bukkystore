from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.catalogue.schemas import (
    CategoryResponse,
    ProductDetailResponse,
    ProductListQuery,
    ProductPageResponse,
    Slug,
)
from bukkystore_api.catalogue.service import (
    InvalidCursorError,
    get_product,
    list_categories,
    list_products,
)
from bukkystore_api.dependencies import get_session
from bukkystore_api.errors import ApiError
from bukkystore_api.schemas import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["Catalogue"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List active store categories",
)
async def categories(session: Session) -> list[CategoryResponse]:
    """Return active categories in their configured display order."""

    return await list_categories(session)


@router.get(
    "/products",
    response_model=ProductPageResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Browse active products",
)
async def products(
    session: Session,
    filters: Annotated[ProductListQuery, Query()],
) -> ProductPageResponse:
    """Return a cursor-paginated catalogue with server-derived availability."""

    if (
        filters.min_price_minor is not None
        and filters.max_price_minor is not None
        and filters.min_price_minor > filters.max_price_minor
    ):
        raise ApiError(400, "invalid_price_range", "Minimum price cannot exceed maximum price.")
    try:
        return await list_products(session, filters)
    except InvalidCursorError as exc:
        raise ApiError(400, "invalid_cursor", "The product cursor is invalid.") from exc


@router.get(
    "/products/{slug}",
    response_model=ProductDetailResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get one active product",
)
async def product_detail(slug: Slug, session: Session) -> ProductDetailResponse:
    """Return product images and selectable variants by human-readable slug."""

    product = await get_product(session, slug)
    if product is None:
        raise ApiError(404, "product_not_found", "The requested product was not found.")
    return product
