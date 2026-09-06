from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from bukkystore_api.admin_catalogue.schemas import (
    AdminCategoryUpdate,
    AdminProductCreate,
    AdminProductUpdate,
    AdminVariantCreate,
    StockAdjustmentRequest,
)
from bukkystore_api.catalogue.models import ProductStatus


def _variant(**overrides: object) -> AdminVariantCreate:
    values = {
        "sku": "DRESS-BRN-M",
        "colour": "Brown",
        "size": "M",
        "display_name": "Brown / M",
        "initial_stock": 3,
    }
    values.update(overrides)
    return AdminVariantCreate.model_validate(values)


def test_product_create_accepts_valid_variants() -> None:
    product = AdminProductCreate(
        category_id=uuid4(),
        name="Brown Dress",
        slug="brown-dress",
        base_price_minor=25_000_00,
        compare_at_price_minor=30_000_00,
        variants=[_variant()],
    )

    assert product.variants[0].initial_stock == 3


def test_product_create_accepts_variants_without_skus() -> None:
    product = AdminProductCreate(
        category_id=uuid4(),
        name="Brown Dress",
        slug="brown-dress",
        base_price_minor=25_000_00,
        variants=[
            _variant(sku=None, size="M"),
            _variant(sku=None, size="L"),
        ],
    )

    assert [variant.sku for variant in product.variants] == [None, None]


@pytest.mark.parametrize(
    "variants",
    [
        [_variant(), _variant(size="L")],
        [_variant(), _variant(sku="OTHER")],
    ],
)
def test_product_create_rejects_duplicate_sku_or_options(
    variants: list[AdminVariantCreate],
) -> None:
    with pytest.raises(ValidationError):
        AdminProductCreate(
            category_id=uuid4(),
            name="Brown Dress",
            slug="brown-dress",
            base_price_minor=25_000_00,
            variants=variants,
        )


def test_product_create_rejects_invalid_compare_at_price() -> None:
    with pytest.raises(ValidationError):
        AdminProductCreate(
            category_id=uuid4(),
            name="Brown Dress",
            slug="brown-dress",
            base_price_minor=25_000_00,
            compare_at_price_minor=20_000_00,
            variants=[_variant()],
        )


def test_stock_adjustment_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        StockAdjustmentRequest(quantity_delta=0, reason="No change")


@pytest.mark.parametrize("payload", [{}, {"name": None}])
def test_category_update_rejects_empty_or_null_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AdminCategoryUpdate.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [{}, {"name": None}, {"status": ProductStatus.ARCHIVED}],
)
def test_product_update_rejects_empty_null_or_archive(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AdminProductUpdate.model_validate(payload)


def test_product_update_allows_clearing_compare_at_price() -> None:
    payload = AdminProductUpdate(compare_at_price_minor=None)

    assert payload.model_fields_set == {"compare_at_price_minor"}


def test_product_create_requires_archive_action() -> None:
    with pytest.raises(ValidationError):
        AdminProductCreate(
            category_id=uuid4(),
            name="Brown Dress",
            slug="brown-dress",
            base_price_minor=25_000_00,
            status=ProductStatus.ARCHIVED,
            variants=[_variant()],
        )
