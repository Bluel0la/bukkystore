from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from bukkystore_api.admin_catalogue.schemas import (
    AdminCategoryCreate,
    AdminCategoryUpdate,
    AdminProductCreate,
    AdminProductListQuery,
    AdminProductPage,
    AdminProductResponse,
    AdminProductUpdate,
    AdminVariantResponse,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
)
from bukkystore_api.catalogue.models import (
    Category,
    InventoryMovement,
    InventoryMovementType,
    Product,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.catalogue.schemas import CategoryResponse
from bukkystore_api.errors import ApiError


def _category_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
    )


def _variant_response(variant: ProductVariant) -> AdminVariantResponse:
    return AdminVariantResponse(
        id=variant.id,
        sku=variant.sku,
        colour=variant.colour,
        size=variant.size,
        display_name=variant.display_name,
        price_override_minor=variant.price_override_minor,
        stock_on_hand=variant.stock_on_hand,
        reserved_quantity=variant.reserved_quantity,
        available_quantity=variant.available_quantity,
        low_stock_threshold=variant.low_stock_threshold,
        status=variant.status,
    )


def _product_response(product: Product) -> AdminProductResponse:
    return AdminProductResponse(
        id=product.id,
        category=_category_response(product.category),
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price_minor=product.base_price_minor,
        compare_at_price_minor=product.compare_at_price_minor,
        currency=product.currency,
        status=product.status,
        featured=product.featured,
        variants=[_variant_response(variant) for variant in product.variants],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _encode_cursor(product: Product) -> str:
    value = [product.created_at.isoformat(), str(product.id)]
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError
        return datetime.fromisoformat(value[0]), UUID(value[1])
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiError(400, "invalid_cursor", "The product cursor is invalid.") from exc


async def list_admin_categories(session: AsyncSession) -> list[CategoryResponse]:
    categories = (
        await session.scalars(select(Category).order_by(Category.display_position, Category.name))
    ).all()
    return [_category_response(category) for category in categories]


async def create_category(session: AsyncSession, payload: AdminCategoryCreate) -> CategoryResponse:
    if payload.parent_id is not None:
        parent = await session.get(Category, payload.parent_id)
        if parent is None:
            raise ApiError(404, "category_parent_not_found", "The parent category was not found.")
    category = Category(**payload.model_dump())
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "category_conflict", "The category slug is already in use.") from exc
    return _category_response(category)


async def update_category(
    session: AsyncSession, category_id: UUID, payload: AdminCategoryUpdate
) -> CategoryResponse:
    category = await session.get(Category, category_id)
    if category is None:
        raise ApiError(404, "category_not_found", "The category was not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "category_conflict", "The category slug is already in use.") from exc
    return _category_response(category)


async def list_admin_products(
    session: AsyncSession, filters: AdminProductListQuery
) -> AdminProductPage:
    statement = select(Product).options(
        joinedload(Product.category), selectinload(Product.variants)
    )
    if filters.search:
        escaped = filters.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Product.name.ilike(f"%{escaped}%", escape="\\"))
    if filters.status:
        statement = statement.where(Product.status == filters.status)
    if filters.category_id:
        statement = statement.where(Product.category_id == filters.category_id)
    if filters.cursor:
        created_at, product_id = _decode_cursor(filters.cursor)
        statement = statement.where(
            (Product.created_at < created_at)
            | ((Product.created_at == created_at) & (Product.id < product_id))
        )
    statement = statement.order_by(Product.created_at.desc(), Product.id.desc()).limit(
        filters.limit + 1
    )
    products = list((await session.scalars(statement)).unique().all())
    visible = products[: filters.limit]
    return AdminProductPage(
        items=[_product_response(product) for product in visible],
        next_cursor=_encode_cursor(visible[-1]) if len(products) > filters.limit else None,
    )


async def get_admin_product(session: AsyncSession, product_id: UUID) -> AdminProductResponse:
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .options(joinedload(Product.category), selectinload(Product.variants))
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    return _product_response(product)


async def create_product(
    session: AsyncSession, payload: AdminProductCreate, actor_user_id: UUID
) -> AdminProductResponse:
    category = await session.get(Category, payload.category_id)
    if category is None or not category.is_active:
        raise ApiError(404, "category_not_found", "An active category was not found.")
    product = Product(
        id=uuid4(),
        category=category,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        base_price_minor=payload.base_price_minor,
        compare_at_price_minor=payload.compare_at_price_minor,
        status=payload.status,
        featured=payload.featured,
    )
    for item in payload.variants:
        variant = ProductVariant(
            sku=item.sku.upper(),
            colour=item.colour,
            size=item.size,
            display_name=item.display_name,
            price_override_minor=item.price_override_minor,
            stock_on_hand=item.initial_stock,
            reserved_quantity=0,
            low_stock_threshold=item.low_stock_threshold,
            status=VariantStatus.ACTIVE,
        )
        if item.initial_stock:
            variant.movements.append(
                InventoryMovement(
                    movement_type=InventoryMovementType.INITIAL_STOCK,
                    quantity_delta=item.initial_stock,
                    reason="Initial stock during product creation",
                    idempotency_key=f"product-create:{product.id}:{variant.sku}",
                    actor_user_id=actor_user_id,
                )
            )
        product.variants.append(variant)
    session.add(product)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(
            409, "product_conflict", "The product slug, SKU, or option combination is in use."
        ) from exc
    return _product_response(product)


async def update_product(
    session: AsyncSession,
    product_id: UUID,
    payload: AdminProductUpdate,
) -> AdminProductResponse:
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .options(joinedload(Product.category), selectinload(Product.variants))
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    values = payload.model_dump(exclude_unset=True)
    if "category_id" in values:
        category = await session.get(Category, values.pop("category_id"))
        if category is None or not category.is_active:
            raise ApiError(404, "category_not_found", "An active category was not found.")
        product.category = category
    for field, value in values.items():
        setattr(product, field, value)
    if (
        product.compare_at_price_minor is not None
        and product.compare_at_price_minor <= product.base_price_minor
    ):
        raise ApiError(400, "invalid_price", "Compare-at price must exceed the selling price.")
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "product_conflict", "The product slug is already in use.") from exc
    return _product_response(product)


async def archive_product(session: AsyncSession, product_id: UUID) -> AdminProductResponse:
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
                .options(joinedload(Product.category), selectinload(Product.variants))
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    product.status = ProductStatus.ARCHIVED
    for variant in product.variants:
        variant.status = VariantStatus.ARCHIVED
    await session.commit()
    return _product_response(product)


async def adjust_stock(
    session: AsyncSession,
    variant_id: UUID,
    payload: StockAdjustmentRequest,
    *,
    idempotency_key: str,
    actor_user_id: UUID,
) -> StockAdjustmentResponse:
    existing = await session.scalar(
        select(InventoryMovement).where(InventoryMovement.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if (
            existing.variant_id != variant_id
            or existing.quantity_delta != payload.quantity_delta
            or existing.reason != payload.reason
        ):
            raise ApiError(409, "idempotency_conflict", "The idempotency key was already used.")
        variant = await session.get(ProductVariant, variant_id)
        if variant is None:
            raise ApiError(404, "variant_not_found", "The product variant was not found.")
        return StockAdjustmentResponse(variant=_variant_response(variant), idempotent_replay=True)

    variant = await session.scalar(
        select(ProductVariant).where(ProductVariant.id == variant_id).with_for_update()
    )
    if variant is None or variant.status is VariantStatus.ARCHIVED:
        raise ApiError(404, "variant_not_found", "An active product variant was not found.")
    new_stock = variant.stock_on_hand + payload.quantity_delta
    if new_stock < variant.reserved_quantity:
        raise ApiError(
            409,
            "stock_below_reserved",
            "Stock cannot be reduced below the quantity reserved for checkout.",
        )
    variant.stock_on_hand = new_stock
    session.add(
        InventoryMovement(
            variant=variant,
            movement_type=InventoryMovementType.ADMIN_ADJUSTMENT,
            quantity_delta=payload.quantity_delta,
            reason=payload.reason,
            idempotency_key=idempotency_key,
            actor_user_id=actor_user_id,
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(
            409, "idempotency_conflict", "The idempotency key was already used."
        ) from exc
    return StockAdjustmentResponse(variant=_variant_response(variant), idempotent_replay=False)
