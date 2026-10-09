from __future__ import annotations

from bukkystore_api.catalogue.models import Product, ProductStatus, ProductVariant


def product() -> Product:
    return Product(
        name="Test Product",
        slug="test-product",
        description="Test description",
        base_price_minor=10_000,
        currency="NGN",
        status=ProductStatus.ACTIVE,
    )


def test_available_quantity_excludes_reservations() -> None:
    variant = ProductVariant(
        product=product(),
        sku="TEST-ONE",
        display_name="Medium",
        size="M",
        stock_on_hand=5,
        reserved_quantity=2,
    )

    assert variant.available_quantity == 3


def test_zero_price_override_is_not_replaced_by_base_price() -> None:
    variant = ProductVariant(
        product=product(),
        sku="TEST-FREE",
        display_name="Default",
        price_override_minor=0,
        stock_on_hand=1,
        reserved_quantity=0,
    )

    assert variant.effective_price_minor == 0


def test_base_price_is_used_without_variant_override() -> None:
    variant = ProductVariant(
        product=product(),
        sku="TEST-BASE",
        display_name="Default",
        stock_on_hand=1,
        reserved_quantity=0,
    )

    assert variant.effective_price_minor == 10_000
