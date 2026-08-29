from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_catalogue.schemas import (
    AdminCategoryCreate,
    AdminCategoryUpdate,
    AdminProductCreate,
    AdminProductListQuery,
    AdminProductUpdate,
    AdminVariantCreate,
    StockAdjustmentRequest,
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
from bukkystore_api.catalogue.models import (
    Category,
    InventoryMovement,
    Product,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.errors import ApiError


class ScalarItems:
    def __init__(self, items: list[Product]) -> None:
        self.items = items

    def unique(self) -> ScalarItems:
        return self

    def all(self) -> list[Product]:
        return self.items

    def one_or_none(self) -> Product | None:
        return self.items[0] if self.items else None


class CategoryItems:
    def __init__(self, items: list[Category]) -> None:
        self.items = items

    def all(self) -> list[Category]:
        return self.items


def _product() -> Product:
    category = Category(id=uuid4(), name="Dresses", slug="dresses")
    product = Product(
        id=uuid4(),
        category=category,
        name="Brown Dress",
        slug="brown-dress",
        description="A dress",
        base_price_minor=25_000_00,
        compare_at_price_minor=None,
        currency="NGN",
        status=ProductStatus.ACTIVE,
        featured=False,
    )
    product.created_at = datetime.now(UTC)
    product.updated_at = datetime.now(UTC)
    product.variants.append(
        ProductVariant(
            id=uuid4(),
            sku="DRESS-M",
            display_name="Brown / M",
            colour="Brown",
            size="M",
            stock_on_hand=4,
            reserved_quantity=1,
            low_stock_threshold=2,
            status=VariantStatus.ACTIVE,
        )
    )
    return product


async def test_admin_list_and_detail_include_exact_stock() -> None:
    product = _product()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([product]))

    page = await list_admin_products(session, AdminProductListQuery(limit=10))
    detail = await get_admin_product(session, product.id)

    assert page.items[0].variants[0].stock_on_hand == 4
    assert page.items[0].variants[0].available_quantity == 3
    assert detail.id == product.id


async def test_category_create_list_update_and_conflicts() -> None:
    parent = Category(id=uuid4(), name="Clothing", slug="clothing", is_active=True)
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=parent)

    async def commit() -> None:
        if session.add.called and session.add.call_args.args[0].id is None:
            session.add.call_args.args[0].id = uuid4()

    session.commit = AsyncMock(side_effect=commit)
    session.scalars = AsyncMock(return_value=CategoryItems([parent]))

    created = await create_category(
        session,
        AdminCategoryCreate(name="Dresses", slug="dresses", parent_id=parent.id),
    )
    listed = await list_admin_categories(session)
    session.get = AsyncMock(return_value=parent)
    updated = await update_category(
        session, parent.id, AdminCategoryUpdate(name="All Clothing", is_active=False)
    )

    assert created.parent_id == parent.id
    assert listed[0].slug == "clothing"
    assert updated.name == "All Clothing"
    assert parent.is_active is False

    session.get = AsyncMock(return_value=None)
    with pytest.raises(ApiError):
        await create_category(
            session,
            AdminCategoryCreate(name="Missing Parent", slug="missing-parent", parent_id=uuid4()),
        )
    with pytest.raises(ApiError):
        await update_category(session, uuid4(), AdminCategoryUpdate(name="Missing"))


async def test_category_maps_unique_constraint_to_conflict() -> None:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate")))
    session.rollback = AsyncMock()

    with pytest.raises(ApiError) as error:
        await create_category(session, AdminCategoryCreate(name="Dresses", slug="dresses"))

    assert error.value.status_code == 409


async def test_create_product_builds_initial_stock_ledger() -> None:
    category = Category(id=uuid4(), name="Dresses", slug="dresses", is_active=True)
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=category)

    async def commit() -> None:
        product = session.add.call_args.args[0]
        product.id = uuid4()
        product.created_at = datetime.now(UTC)
        product.updated_at = datetime.now(UTC)
        product.currency = "NGN"
        for variant in product.variants:
            variant.id = uuid4()

    session.commit = AsyncMock(side_effect=commit)
    payload = AdminProductCreate(
        category_id=category.id,
        name="New Dress",
        slug="new-dress",
        base_price_minor=20_000_00,
        variants=[
            AdminVariantCreate(sku="NEW-M", display_name="Medium", size="M", initial_stock=3)
        ],
    )

    created = await create_product(session, payload, uuid4())

    assert created.variants[0].stock_on_hand == 3
    product = session.add.call_args.args[0]
    assert len(product.variants[0].movements) == 1


async def test_create_product_rejects_missing_category() -> None:
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=None)
    payload = AdminProductCreate(
        category_id=uuid4(),
        name="New Dress",
        slug="new-dress",
        base_price_minor=20_000_00,
        variants=[AdminVariantCreate(sku="NEW", display_name="Default")],
    )

    with pytest.raises(ApiError) as error:
        await create_product(session, payload, uuid4())

    assert error.value.status_code == 404


async def test_admin_list_filters_and_rejects_invalid_cursor() -> None:
    product = _product()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([product]))
    filters = AdminProductListQuery(
        search="Dress%_\\",
        status=ProductStatus.ACTIVE,
        category_id=product.category.id,
        limit=1,
    )
    page = await list_admin_products(session, filters)
    assert page.items[0].id == product.id

    with pytest.raises(ApiError) as error:
        await list_admin_products(session, AdminProductListQuery(cursor="invalid"))
    assert error.value.code == "invalid_cursor"


async def test_update_and_archive_product() -> None:
    product = _product()
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([product]))
    session.commit = AsyncMock()

    updated = await update_product(
        session, product.id, AdminProductUpdate(name="Updated Dress", featured=True)
    )
    archived = await archive_product(session, product.id)

    assert updated.name == "Updated Dress"
    assert archived.status is ProductStatus.ARCHIVED
    assert archived.variants[0].status is VariantStatus.ARCHIVED


async def test_update_rejects_missing_or_invalid_product_state() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=ScalarItems([]))
    with pytest.raises(ApiError):
        await get_admin_product(session, uuid4())
    with pytest.raises(ApiError):
        await update_product(session, uuid4(), AdminProductUpdate(name="Missing"))
    with pytest.raises(ApiError):
        await archive_product(session, uuid4())

    product = _product()
    session.scalars = AsyncMock(return_value=ScalarItems([product]))
    session.get = AsyncMock(return_value=None)
    with pytest.raises(ApiError) as category_error:
        await update_product(session, product.id, AdminProductUpdate(category_id=uuid4()))
    assert category_error.value.code == "category_not_found"

    with pytest.raises(ApiError) as price_error:
        await update_product(
            session,
            product.id,
            AdminProductUpdate(base_price_minor=30_000_00, compare_at_price_minor=20_000_00),
        )
    assert price_error.value.code == "invalid_price"


async def test_stock_adjustment_updates_counter_and_ledger() -> None:
    variant = _product().variants[0]
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(side_effect=[None, variant])
    session.commit = AsyncMock()

    response = await adjust_stock(
        session,
        variant.id,
        StockAdjustmentRequest(quantity_delta=2, reason="New delivery"),
        idempotency_key="stock-test-key",
        actor_user_id=uuid4(),
    )

    assert response.variant.stock_on_hand == 6
    assert response.idempotent_replay is False
    assert isinstance(session.add.call_args.args[0], InventoryMovement)


async def test_stock_adjustment_rejects_below_reserved_and_conflicting_replay() -> None:
    variant = _product().variants[0]
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(side_effect=[None, variant])
    with pytest.raises(ApiError) as stock_error:
        await adjust_stock(
            session,
            variant.id,
            StockAdjustmentRequest(quantity_delta=-4, reason="Correction"),
            idempotency_key="stock-low",
            actor_user_id=uuid4(),
        )
    assert stock_error.value.code == "stock_below_reserved"

    movement = InventoryMovement(
        variant_id=variant.id,
        quantity_delta=1,
        reason="Different",
        idempotency_key="used-key",
    )
    session.scalar = AsyncMock(return_value=movement)
    with pytest.raises(ApiError) as replay_error:
        await adjust_stock(
            session,
            variant.id,
            StockAdjustmentRequest(quantity_delta=2, reason="New delivery"),
            idempotency_key="used-key",
            actor_user_id=uuid4(),
        )
    assert replay_error.value.code == "idempotency_conflict"


async def test_stock_adjustment_replays_matching_request() -> None:
    variant = _product().variants[0]
    movement = InventoryMovement(
        variant_id=variant.id,
        quantity_delta=2,
        reason="New delivery",
        idempotency_key="used-key",
    )
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=movement)
    session.get = AsyncMock(return_value=variant)

    replay = await adjust_stock(
        session,
        variant.id,
        StockAdjustmentRequest(quantity_delta=2, reason="New delivery"),
        idempotency_key="used-key",
        actor_user_id=uuid4(),
    )

    assert replay.idempotent_replay is True
