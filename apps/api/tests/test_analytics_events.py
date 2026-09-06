from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.admin_analytics.schemas import AnalyticsRangeQuery
from bukkystore_api.admin_analytics.service import get_product_engagement
from bukkystore_api.analytics import router as analytics_router
from bukkystore_api.analytics.schemas import AnalyticsEventCreate
from bukkystore_api.analytics.service import (
    product_engagement_counts,
    record_event,
    top_engaged_products,
)
from bukkystore_api.auth.dependencies import require_admin
from bukkystore_api.catalogue.models import Product
from bukkystore_api.errors import ApiError


def _payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "event_type": "whatsapp_click",
        "session_id": "session-1234",
        "source": "tiktok",
    }
    base.update(overrides)
    return base


def _mock_session(
    *,
    get_result: Any = None,
    execute_result: Any = None,
) -> Any:
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=get_result)
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


class Rows:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def all(self) -> list[object]:
        return self.items


def test_event_schema_rejects_unknown_types_fields_and_sources() -> None:
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(**_payload(event_type="purchase"))
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(**_payload(session_id="short"))
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(**_payload(event_type="whatsapp_click", extra="field"))
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(
            **_payload(metadata={f"key-{n}": "v" for n in range(11)}),
        )


def test_event_schema_normalizes_source_and_campaign() -> None:
    event = AnalyticsEventCreate(**_payload(source="TikTok", campaign=" video1 "))
    assert event.source == "tiktok"
    assert event.campaign == "video1"

    assert AnalyticsEventCreate(**_payload(source="  ")).source == "direct"
    assert AnalyticsEventCreate(**_payload()).source == "tiktok"


async def test_record_event_persists_without_product() -> None:
    session = _mock_session()

    response = await record_event(session, AnalyticsEventCreate(**_payload()))

    assert response.event_type == "whatsapp_click"
    assert response.id is not None
    added = session.add.call_args.args[0]
    assert added.source == "tiktok"
    session.commit.assert_awaited_once()


async def test_record_event_rejects_unknown_product() -> None:
    session = _mock_session(get_result=None)

    with pytest.raises(ApiError) as error:
        await record_event(session, AnalyticsEventCreate(**_payload(product_id=uuid4())))

    assert error.value.status_code == 404
    assert error.value.code == "product_not_found"


async def test_record_event_links_known_product() -> None:
    product = Product(
        id=uuid4(),
        name="Test",
        slug="test",
        description="Test",
        base_price_minor=100,
        currency="NGN",
    )
    session = _mock_session(get_result=product)

    await record_event(
        session,
        AnalyticsEventCreate(**_payload(product_id=product.id, metadata={"channel": "copy"})),
    )

    assert session.add.call_args.args[0].product_id == product.id


async def test_product_engagement_counts_each_type() -> None:
    session = _mock_session(execute_result=Rows([("product_view", 12), ("whatsapp_click", 3)]))

    counts = await product_engagement_counts(
        session, product_id=uuid4(), period_start=datetime.now(UTC)
    )

    assert counts == {"views": 12, "shares": 0, "whatsapp_clicks": 3}


async def test_top_engaged_products_orders_by_views() -> None:
    first, second = uuid4(), uuid4()
    session = _mock_session(execute_result=Rows([(first, "Dress", 12, 3), (second, "Bag", 4, 0)]))

    top = await top_engaged_products(session, period_start=datetime.now(UTC))

    assert [(item["product_id"], item["views"]) for item in top] == [(first, 12), (second, 4)]


async def test_get_product_engagement_returns_windowed_counts() -> None:
    product_id = uuid4()
    product = Product(
        id=product_id,
        name="Dress",
        slug="dress",
        description="Dress",
        base_price_minor=100,
        currency="NGN",
    )
    session = _mock_session(get_result=product)
    session.execute = AsyncMock(
        return_value=Rows([("product_view", 7), ("share_click", 2), ("whatsapp_click", 1)])
    )

    response = await get_product_engagement(session, product_id, AnalyticsRangeQuery(days=7))

    assert response.product_name == "Dress"
    assert response.range_days == 7
    assert (response.views, response.shares, response.whatsapp_clicks) == (7, 2, 1)


async def test_get_product_engagement_missing_product_is_not_found() -> None:
    with pytest.raises(ApiError) as error:
        await get_product_engagement(_mock_session(get_result=None), uuid4(), AnalyticsRangeQuery())

    assert error.value.status_code == 404


async def test_analytics_ingestion_is_public_but_validated(client: AsyncClient) -> None:
    accepted = await client.post("/api/v1/analytics/events", json=_payload())
    unknown_product = await client.post(
        "/api/v1/analytics/events", json=_payload(product_id=str(uuid4()))
    )
    invalid = await client.post("/api/v1/analytics/events", json=_payload(event_type="purchase"))

    assert accepted.status_code == 201
    assert accepted.json()["event_type"] == "whatsapp_click"
    assert unknown_product.status_code == 404
    assert invalid.status_code == 422


async def test_analytics_ingestion_enforces_rate_limit(client: AsyncClient) -> None:
    analytics_router.reset_rate_limiter()
    statuses: list[int] = []
    for _ in range(31):
        response = await client.post("/api/v1/analytics/events", json=_payload())
        statuses.append(response.status_code)
    analytics_router.reset_rate_limiter()

    assert statuses[:30] == [201] * 30
    assert statuses[30] == 429


async def test_product_engagement_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/admin/analytics/products/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


async def test_product_engagement_wiring(client: AsyncClient, app: Any, monkeypatch: Any) -> None:
    from bukkystore_api.admin_analytics import router as admin_analytics_router

    product_id = uuid4()
    expected = SimpleNamespace(
        product_id=product_id,
        product_name="Dress",
        range_days=30,
        period_start=datetime.now(UTC),
        views=5,
        shares=1,
        whatsapp_clicks=2,
    )
    monkeypatch.setattr(
        admin_analytics_router, "get_product_engagement", AsyncMock(return_value=expected)
    )
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace()

    response = await client.get(f"/api/v1/admin/analytics/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["whatsapp_clicks"] == 2
