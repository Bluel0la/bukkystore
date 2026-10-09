from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from bukkystore_api.catalogue.models import (
    Category,
    Product,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.catalogue.schemas import ProductListQuery
from bukkystore_api.catalogue.service import (
    InvalidCursorError,
    _card_response,
    _decode_cursor,
    _encode_cursor,
)


def catalogue_product(*, featured: bool = False) -> Product:
    category = Category(id=uuid4(), name="Dresses", slug="dresses")
    product = Product(
        id=uuid4(),
        category=category,
        name="Brown Linen Dress",
        slug="brown-linen-dress",
        description="A breathable linen dress.",
        base_price_minor=1_850_000,
        currency="NGN",
        status=ProductStatus.ACTIVE,
        featured=featured,
        created_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    product.variants.extend(
        [
            ProductVariant(
                id=uuid4(),
                product=product,
                sku="BLD-S",
                display_name="Brown / Small",
                colour="Brown",
                size="S",
                stock_on_hand=2,
                reserved_quantity=0,
                low_stock_threshold=2,
                status=VariantStatus.ACTIVE,
            ),
            ProductVariant(
                id=uuid4(),
                product=product,
                sku="BLD-M",
                display_name="Brown / Medium",
                colour="Brown",
                size="M",
                stock_on_hand=1,
                reserved_quantity=1,
                low_stock_threshold=2,
                status=VariantStatus.ACTIVE,
            ),
        ]
    )
    return product


def test_product_card_derives_options_and_availability() -> None:
    response = _card_response(catalogue_product())

    assert response.available is True
    assert response.colours == ["Brown"]
    assert response.sizes == ["M", "S"]
    assert response.primary_image is None


def test_cursor_round_trip_preserves_sort_values() -> None:
    product = catalogue_product(featured=True)

    featured, created_at, product_id = _decode_cursor(_encode_cursor(product))

    assert featured is True
    assert created_at == product.created_at
    assert product_id == product.id


@pytest.mark.parametrize("cursor", ["", "not-base64", "WzEsMiwzXQ"])
def test_invalid_cursor_is_rejected(cursor: str) -> None:
    with pytest.raises(InvalidCursorError):
        _decode_cursor(cursor)


def test_price_range_query_rejects_negative_values() -> None:
    with pytest.raises(ValueError):
        ProductListQuery(min_price_minor=-1)
