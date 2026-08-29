from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select

from bukkystore_api.catalogue.models import (
    Category,
    InventoryMovement,
    InventoryMovementType,
    Product,
    ProductStatus,
    ProductVariant,
    VariantStatus,
)
from bukkystore_api.config import get_settings
from bukkystore_api.database import Database


def _variant(
    product: Product,
    *,
    sku: str,
    display_name: str,
    stock: int,
    colour: str | None = None,
    size: str | None = None,
) -> ProductVariant:
    variant = ProductVariant(
        product=product,
        sku=sku,
        display_name=display_name,
        colour=colour,
        size=size,
        stock_on_hand=stock,
        reserved_quantity=0,
        low_stock_threshold=2,
        status=VariantStatus.ACTIVE,
    )
    if stock > 0:
        variant.movements.append(
            InventoryMovement(
                movement_type=InventoryMovementType.INITIAL_STOCK,
                quantity_delta=stock,
                reason="Development catalogue seed",
                idempotency_key=f"seed:{sku}:{uuid4()}",
            )
        )
    return variant


async def seed_catalogue() -> bool:
    """Create representative local catalogue data once; return whether data was added."""

    database = Database(str(get_settings().database_url))
    try:
        async with database.session_factory.begin() as session:
            existing = await session.scalar(select(Category.id).where(Category.slug == "dresses"))
            if existing is not None:
                return False

            clothing = Category(name="Clothing", slug="clothing", display_position=0)
            dresses = Category(name="Dresses", slug="dresses", parent=clothing, display_position=0)
            shoes = Category(name="Shoes", slug="shoes", display_position=1)
            bags = Category(name="Bags", slug="bags", display_position=2)

            dress = Product(
                category=dresses,
                name="Brown Linen Dress",
                slug="brown-linen-dress",
                description=(
                    "An easy, breathable linen dress with a softly structured shape for "
                    "warm Lagos days."
                ),
                base_price_minor=1_850_000,
                currency="NGN",
                status=ProductStatus.ACTIVE,
                featured=True,
            )
            dress.variants.extend(
                [
                    _variant(
                        dress,
                        sku="BLD-BRN-S",
                        display_name="Brown / Small",
                        colour="Brown",
                        size="S",
                        stock=3,
                    ),
                    _variant(
                        dress,
                        sku="BLD-BRN-M",
                        display_name="Brown / Medium",
                        colour="Brown",
                        size="M",
                        stock=4,
                    ),
                    _variant(
                        dress,
                        sku="BLD-BRN-L",
                        display_name="Brown / Large",
                        colour="Brown",
                        size="L",
                        stock=2,
                    ),
                ]
            )

            heel = Product(
                category=shoes,
                name="Black Evening Heel",
                slug="black-evening-heel",
                description="A clean black heel made for dinners, events, and dressed-up evenings.",
                base_price_minor=2_400_000,
                compare_at_price_minor=2_800_000,
                currency="NGN",
                status=ProductStatus.ACTIVE,
            )
            heel.variants.extend(
                [
                    _variant(
                        heel,
                        sku=f"BEH-BLK-{size}",
                        display_name=f"Black / {size}",
                        colour="Black",
                        size=size,
                        stock=stock,
                    )
                    for size, stock in (("38", 2), ("39", 1), ("40", 3), ("41", 0))
                ]
            )

            bag = Product(
                category=bags,
                name="Cream Day Bag",
                slug="cream-day-bag",
                description="A compact everyday bag with room for the essentials.",
                base_price_minor=1_650_000,
                currency="NGN",
                status=ProductStatus.ACTIVE,
            )
            bag.variants.append(
                _variant(
                    bag,
                    sku="CDB-CRM",
                    display_name="Cream",
                    colour="Cream",
                    stock=5,
                )
            )

            session.add_all([clothing, dresses, shoes, bags, dress, heel, bag])
        return True
    finally:
        await database.dispose()


def main() -> None:
    created = asyncio.run(seed_catalogue())
    print("Development catalogue created." if created else "Development catalogue already exists.")


if __name__ == "__main__":
    main()
