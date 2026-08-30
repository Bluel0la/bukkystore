from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_analytics.schemas import AnalyticsRangeQuery
from bukkystore_api.admin_analytics.service import get_admin_analytics_overview


class Rows:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def all(self) -> list[object]:
        return self.items

    def one(self) -> object:
        return self.items[0]


async def test_overview_maps_bounded_operational_aggregates() -> None:
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    product_id = uuid4()
    variant_id = uuid4()
    metrics = SimpleNamespace(
        total_orders=7,
        sales_orders=5,
        sales_minor=550_000,
        awaiting_payment_orders=1,
        open_fulfilment_orders=2,
    )
    low_stock = SimpleNamespace(
        variant_id=variant_id,
        product_id=product_id,
        product_name="Brown Linen Dress",
        variant_name="Brown / M",
        sku="DRESS-BRN-M",
        available_quantity=1,
        low_stock_threshold=2,
        total_low_stock=3,
    )
    top_product = SimpleNamespace(
        product_id=product_id,
        product_name="Brown Linen Dress",
        units_sold=4,
        sales_minor=400_000,
    )
    source = SimpleNamespace(source="instagram", orders=3, sales_minor=330_000)
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(
        side_effect=[Rows([metrics]), Rows([low_stock]), Rows([top_product]), Rows([source])]
    )
    session.scalar = AsyncMock(return_value=2)

    overview = await get_admin_analytics_overview(session, AnalyticsRangeQuery(days=30), now=now)

    assert overview.generated_at == now
    assert overview.range_days == 30
    assert overview.total_orders == 7
    assert overview.sales_minor == 550_000
    assert overview.average_order_minor == 110_000
    assert overview.pending_refunds == 2
    assert overview.low_stock_variants == 3
    assert overview.low_stock[0].available_quantity == 1
    assert overview.top_products[0].units_sold == 4
    assert overview.sources[0].source == "instagram"
    assert session.execute.await_count == 4


async def test_overview_handles_empty_sales_without_division_or_missing_counts() -> None:
    metrics = SimpleNamespace(
        total_orders=0,
        sales_orders=0,
        sales_minor=0,
        awaiting_payment_orders=0,
        open_fulfilment_orders=0,
    )
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(side_effect=[Rows([metrics]), Rows([]), Rows([]), Rows([])])
    session.scalar = AsyncMock(return_value=None)

    overview = await get_admin_analytics_overview(session, AnalyticsRangeQuery())

    assert overview.average_order_minor == 0
    assert overview.pending_refunds == 0
    assert overview.low_stock_variants == 0
    assert overview.top_products == []
    assert overview.sources == []


@pytest.mark.parametrize("days", [0, 366])
def test_analytics_range_rejects_unbounded_windows(days: int) -> None:
    with pytest.raises(ValidationError):
        AnalyticsRangeQuery(days=days)
