from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from bukkystore_api.admin_catalogue.cloudinary import (
    delivery_url,
    destroy_image,
    require_cloudinary,
    sign_parameters,
    verify_upload_response,
)
from bukkystore_api.admin_catalogue.schemas import (
    AdminCategoryCreate,
    AdminCategoryUpdate,
    AdminProductCreate,
    AdminProductImageResponse,
    AdminProductListQuery,
    AdminProductPage,
    AdminProductResponse,
    AdminProductUpdate,
    AdminVariantResponse,
    ImageUploadSignatureResponse,
    ProductImageRegisterRequest,
    ProductImageReorderRequest,
    ProductImageUpdateRequest,
    StockAdjustmentRequest,
    StockAdjustmentResponse,
)
from bukkystore_api.catalogue.models import (
    Category,
    InventoryMovement,
    InventoryMovementType,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.catalogue.schemas import CategoryResponse
from bukkystore_api.config import Settings
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


def _image_response(image: ProductImage) -> AdminProductImageResponse:
    return AdminProductImageResponse(
        id=image.id,
        public_id=image.cloudinary_public_id,
        url=image.secure_url,
        alt_text=image.alt_text,
        width=image.width,
        height=image.height,
        position=image.position,
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
        images=[_image_response(image) for image in product.images],
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


def _alnum_upper(value: str) -> str:
    return "".join(char for char in value.upper() if char.isalnum())


def generate_sku(
    product_name: str, colour: str | None, size: str | None, *, taken: set[str]
) -> str:
    """Build a human-readable SKU and resolve collisions with a numeric suffix.

    Brown Linen Dress + Brown + M becomes BLD-BRN-M. `taken` holds casefolded
    SKUs already used in this request or found in the database.
    """

    words = [_alnum_upper(word) for word in product_name.split()]
    words = [word for word in words if word]
    if len(words) >= 2:
        head = "".join(word[0] for word in words[:3])
    elif words:
        head = words[0][:3]
    else:
        head = "ITEM"
    segments = [head]
    if colour and _alnum_upper(colour):
        segments.append(_alnum_upper(colour)[:3])
    if size and _alnum_upper(size):
        segments.append(_alnum_upper(size)[:8])
    base = "-".join(segments)[:80]
    candidate = base
    suffix = 2
    while candidate.casefold() in taken:
        tail = f"-{suffix}"
        candidate = f"{base[: 80 - len(tail)]}{tail}"
        suffix += 1
        if suffix > 999:
            raise ApiError(409, "product_conflict", "A unique SKU could not be generated.")
    taken.add(candidate.casefold())
    return candidate


async def _unique_generated_sku(
    session: AsyncSession,
    product_name: str,
    colour: str | None,
    size: str | None,
    *,
    taken: set[str],
) -> str:
    """Generate a SKU that is free in this request and in the database."""

    for _ in range(25):
        candidate = generate_sku(product_name, colour, size, taken=taken)
        exists = await session.scalar(
            select(ProductVariant.id).where(ProductVariant.sku == candidate)
        )
        if exists is None:
            return candidate
    raise ApiError(409, "product_conflict", "A unique SKU could not be generated.")


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
        joinedload(Product.category), selectinload(Product.variants), selectinload(Product.images)
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
                .options(
                    joinedload(Product.category),
                    selectinload(Product.variants),
                    selectinload(Product.images),
                )
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
    taken = {item.sku.casefold() for item in payload.variants if item.sku}
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
        sku = item.sku.upper() if item.sku else None
        if sku is None:
            sku = await _unique_generated_sku(
                session, payload.name, item.colour, item.size, taken=taken
            )
        else:
            taken.add(sku.casefold())
        variant = ProductVariant(
            sku=sku,
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
                .options(
                    joinedload(Product.category),
                    selectinload(Product.variants),
                    selectinload(Product.images),
                )
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


async def _locked_product(session: AsyncSession, product_id: UUID) -> Product:
    # NOTE: the lock and the eager loads must not produce a JOIN. PostgreSQL
    # rejects bare FOR UPDATE over an outer join, so everything here uses
    # selectinload (separate queries, same no-N+1 guarantee).
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
                .options(
                    selectinload(Product.category),
                    selectinload(Product.variants),
                    selectinload(Product.images),
                )
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    return product


async def archive_product(session: AsyncSession, product_id: UUID) -> AdminProductResponse:
    product = await _locked_product(session, product_id)
    product.status = ProductStatus.ARCHIVED
    for variant in product.variants:
        variant.status = VariantStatus.ARCHIVED
    await session.commit()
    return _product_response(product)


async def unarchive_product(session: AsyncSession, product_id: UUID) -> AdminProductResponse:
    """Restore an archived product (and its variants) to published status."""

    product = await _locked_product(session, product_id)
    product.status = ProductStatus.ACTIVE
    for variant in product.variants:
        variant.status = VariantStatus.ACTIVE
    await session.commit()
    return _product_response(product)


async def bulk_set_archived(
    session: AsyncSession, product_ids: list[UUID], *, archived: bool
) -> list[UUID]:
    """Archive or restore many products atomically. Fails fast on unknown ids."""

    # NOTE: no joinedload here — PostgreSQL rejects bare FOR UPDATE over the
    # outer join it produces.
    products = (
        await session.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .with_for_update()
            .options(selectinload(Product.variants))
        )
    ).all()
    found = {product.id for product in products}
    if len(found) != len(set(product_ids)):
        raise ApiError(404, "product_not_found", "One or more products were not found.")
    target_product = ProductStatus.ARCHIVED if archived else ProductStatus.ACTIVE
    target_variant = VariantStatus.ARCHIVED if archived else VariantStatus.ACTIVE
    for product in products:
        product.status = target_product
        for variant in product.variants:
            variant.status = target_variant
    await session.commit()
    return sorted(product_ids)


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


async def create_image_upload_signature(
    session: AsyncSession, product_id: UUID, settings: Settings
) -> ImageUploadSignatureResponse:
    product_exists = await session.scalar(select(Product.id).where(Product.id == product_id))
    if product_exists is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    cloud_name, api_key, api_secret = require_cloudinary(settings)
    timestamp = int(datetime.now(UTC).timestamp())
    public_id = f"bukkystore/products/{product_id}/{uuid4()}"
    parameters: dict[str, str | int] = {
        "overwrite": "false",
        "public_id": public_id,
        "timestamp": timestamp,
    }
    return ImageUploadSignatureResponse(
        upload_url=f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        cloud_name=cloud_name,
        api_key=api_key,
        timestamp=timestamp,
        public_id=public_id,
        signature=sign_parameters(parameters, api_secret),
        max_bytes=10_000_000,
        allowed_mime_types=["image/jpeg", "image/png", "image/webp", "image/avif"],
    )


async def register_product_image(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductImageRegisterRequest,
    settings: Settings,
) -> AdminProductImageResponse:
    cloud_name, _api_key, api_secret = require_cloudinary(settings)
    expected_prefix = f"bukkystore/products/{product_id}/"
    if not payload.public_id.startswith(expected_prefix):
        raise ApiError(
            400, "invalid_image_upload", "The uploaded photo does not match this product."
        )
    if not verify_upload_response(
        public_id=payload.public_id,
        version=payload.version,
        signature=payload.signature,
        api_secret=api_secret,
    ):
        raise ApiError(400, "invalid_image_upload", "The image provider response is invalid.")
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
                .options(selectinload(Product.images))
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    existing = next(
        (image for image in product.images if image.cloudinary_public_id == payload.public_id), None
    )
    if existing is not None:
        return _image_response(existing)
    if len(product.images) >= 10:
        raise ApiError(409, "image_limit_reached", "A product can have at most 10 photos.")
    image = ProductImage(
        product=product,
        cloudinary_public_id=payload.public_id,
        secure_url=delivery_url(
            cloud_name=cloud_name,
            public_id=payload.public_id,
            version=payload.version,
            image_format=payload.format,
        ),
        alt_text=payload.alt_text,
        width=payload.width,
        height=payload.height,
        position=len(product.images),
    )
    session.add(image)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "image_conflict", "This photo has already been registered.") from exc
    return _image_response(image)


async def update_product_image(
    session: AsyncSession,
    product_id: UUID,
    image_id: UUID,
    payload: ProductImageUpdateRequest,
) -> AdminProductImageResponse:
    image = await session.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )
    if image is None:
        raise ApiError(404, "image_not_found", "The product photo was not found.")
    image.alt_text = payload.alt_text
    await session.commit()
    return _image_response(image)


async def reorder_product_images(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductImageReorderRequest,
) -> list[AdminProductImageResponse]:
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
                .options(selectinload(Product.images))
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    images_by_id = {image.id: image for image in product.images}
    if set(payload.image_ids) != set(images_by_id):
        raise ApiError(400, "invalid_image_order", "The order must include every product photo.")
    for offset, image_id in enumerate(payload.image_ids, start=1_000_000):
        images_by_id[image_id].position = offset
    await session.flush()
    ordered = []
    for position, image_id in enumerate(payload.image_ids):
        image = images_by_id[image_id]
        image.position = position
        ordered.append(image)
    await session.commit()
    return [_image_response(image) for image in ordered]


async def remove_product_image(
    session: AsyncSession,
    product_id: UUID,
    image_id: UUID,
    settings: Settings,
) -> list[AdminProductImageResponse]:
    product = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
                .options(selectinload(Product.images))
            )
        )
        .unique()
        .one_or_none()
    )
    if product is None:
        raise ApiError(404, "product_not_found", "The product was not found.")
    image = next((item for item in product.images if item.id == image_id), None)
    if image is None:
        raise ApiError(404, "image_not_found", "The product photo was not found.")
    await destroy_image(image.cloudinary_public_id, settings, int(datetime.now(UTC).timestamp()))
    product.images.remove(image)
    await session.delete(image)
    # Delete the old position first so compacting cannot collide with the
    # per-product unique position constraint.
    await session.flush()
    for position, remaining in enumerate(product.images):
        remaining.position = position
    await session.commit()
    return [_image_response(item) for item in product.images]
