from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from bukkystore_api.catalogue.models import (
    Category,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.catalogue.schemas import (
    CategoryResponse,
    ProductCardResponse,
    ProductDetailResponse,
    ProductImageResponse,
    ProductListQuery,
    ProductPageResponse,
    ProductVariantResponse,
)


class InvalidCursorError(ValueError):
    pass


def _image_response(image: ProductImage) -> ProductImageResponse:
    return ProductImageResponse(
        url=image.secure_url,
        alt_text=image.alt_text,
        width=image.width,
        height=image.height,
    )


def _category_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
    )


def _active_variants(product: Product) -> list[ProductVariant]:
    return [variant for variant in product.variants if variant.status is VariantStatus.ACTIVE]


def _card_response(product: Product) -> ProductCardResponse:
    variants = _active_variants(product)
    colours = sorted({variant.colour for variant in variants if variant.colour})
    sizes = sorted({variant.size for variant in variants if variant.size})
    return ProductCardResponse(
        id=product.id,
        name=product.name,
        slug=product.slug,
        category=_category_response(product.category),
        price_minor=product.base_price_minor,
        compare_at_price_minor=product.compare_at_price_minor,
        currency="NGN",
        featured=product.featured,
        available=any(variant.available_quantity > 0 for variant in variants),
        primary_image=_image_response(product.images[0]) if product.images else None,
        colours=colours,
        sizes=sizes,
    )


def _detail_response(product: Product) -> ProductDetailResponse:
    card = _card_response(product)
    variants = _active_variants(product)
    return ProductDetailResponse(
        **card.model_dump(),
        description=product.description,
        images=[_image_response(image) for image in product.images],
        variants=[
            ProductVariantResponse(
                id=variant.id,
                sku=variant.sku,
                colour=variant.colour,
                size=variant.size,
                display_name=variant.display_name,
                price_minor=variant.effective_price_minor,
                currency="NGN",
                available=variant.available_quantity > 0,
                low_stock=0 < variant.available_quantity <= variant.low_stock_threshold,
            )
            for variant in variants
        ],
    )


def _encode_cursor(product: Product) -> str:
    payload = [product.featured, product.created_at.isoformat(), str(product.id)]
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
    return encoded.decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[bool, datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if not isinstance(value, list) or len(value) != 3 or not isinstance(value[0], bool):
            raise ValueError
        return value[0], datetime.fromisoformat(value[1]), UUID(value[2])
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidCursorError("Invalid product cursor") from exc


def _escape_search(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(
    statement: Select[tuple[Product]], filters: ProductListQuery
) -> Select[tuple[Product]]:
    available_variant = and_(
        ProductVariant.status == VariantStatus.ACTIVE,
        ProductVariant.stock_on_hand > ProductVariant.reserved_quantity,
    )
    if filters.category:
        statement = statement.join(Product.category).where(Category.slug == filters.category)
    if filters.search:
        pattern = f"%{_escape_search(filters.search)}%"
        statement = statement.where(Product.name.ilike(pattern, escape="\\"))
    if filters.size:
        statement = statement.where(
            Product.variants.any(
                and_(
                    ProductVariant.status == VariantStatus.ACTIVE,
                    func.lower(ProductVariant.size) == filters.size.lower(),
                )
            )
        )
    if filters.available is True:
        statement = statement.where(Product.variants.any(available_variant))
    elif filters.available is False:
        statement = statement.where(~Product.variants.any(available_variant))
    if filters.featured is not None:
        statement = statement.where(Product.featured.is_(filters.featured))
    if filters.min_price_minor is not None:
        statement = statement.where(Product.base_price_minor >= filters.min_price_minor)
    if filters.max_price_minor is not None:
        statement = statement.where(Product.base_price_minor <= filters.max_price_minor)
    if filters.cursor:
        featured, created_at, product_id = _decode_cursor(filters.cursor)
        within_feature_group = and_(
            Product.featured.is_(featured),
            or_(
                Product.created_at < created_at,
                and_(
                    Product.created_at == created_at,
                    Product.id < product_id,
                ),
            ),
        )
        if featured:
            statement = statement.where(or_(Product.featured.is_(False), within_feature_group))
        else:
            statement = statement.where(within_feature_group)
    return statement


async def list_categories(session: AsyncSession) -> list[CategoryResponse]:
    statement = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.display_position, Category.name)
    )
    categories = (await session.scalars(statement)).all()
    return [_category_response(category) for category in categories]


async def list_products(session: AsyncSession, filters: ProductListQuery) -> ProductPageResponse:
    statement = (
        select(Product)
        .where(Product.status == ProductStatus.ACTIVE)
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants),
        )
    )
    statement = _apply_filters(statement, filters)
    statement = statement.order_by(
        Product.featured.desc(), Product.created_at.desc(), Product.id.desc()
    ).limit(filters.limit + 1)
    products = list((await session.scalars(statement)).unique().all())
    has_more = len(products) > filters.limit
    visible_products = products[: filters.limit]
    return ProductPageResponse(
        items=[_card_response(product) for product in visible_products],
        next_cursor=_encode_cursor(visible_products[-1]) if has_more else None,
    )


async def get_product(session: AsyncSession, slug: str) -> ProductDetailResponse | None:
    statement = (
        select(Product)
        .where(Product.slug == slug, Product.status == ProductStatus.ACTIVE)
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants),
        )
    )
    product = (await session.scalars(statement)).unique().one_or_none()
    return _detail_response(product) if product else None
