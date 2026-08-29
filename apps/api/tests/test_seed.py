from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from bukkystore_api import seed
from bukkystore_api.catalogue.models import Product


class FakeSeedSession:
    def __init__(self, existing: bool) -> None:
        self.existing = existing
        self.added: list[Any] = []

    async def scalar(self, _statement: object) -> object | None:
        return uuid4() if self.existing else None

    def add_all(self, values: list[Any]) -> None:
        self.added.extend(values)


class FakeSessionFactory:
    def __init__(self, session: FakeSeedSession) -> None:
        self.session = session

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[FakeSeedSession]:
        yield self.session


class FakeSeedDatabase:
    def __init__(self, session: FakeSeedSession) -> None:
        self.session_factory = FakeSessionFactory(session)
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


async def test_seed_creates_representative_catalogue(monkeypatch: Any) -> None:
    session = FakeSeedSession(existing=False)
    database = FakeSeedDatabase(session)
    monkeypatch.setattr(seed, "Database", lambda _url: database)
    monkeypatch.setattr(
        seed, "get_settings", lambda: SimpleNamespace(database_url="postgresql://unused")
    )

    created = await seed.seed_catalogue()

    assert created is True
    assert database.disposed is True
    assert {item.slug for item in session.added if hasattr(item, "slug")} >= {
        "dresses",
        "brown-linen-dress",
        "black-evening-heel",
        "cream-day-bag",
    }


async def test_seed_is_idempotent(monkeypatch: Any) -> None:
    session = FakeSeedSession(existing=True)
    database = FakeSeedDatabase(session)
    monkeypatch.setattr(seed, "Database", lambda _url: database)
    monkeypatch.setattr(
        seed, "get_settings", lambda: SimpleNamespace(database_url="postgresql://unused")
    )

    created = await seed.seed_catalogue()

    assert created is False
    assert session.added == []
    assert database.disposed is True


def test_zero_stock_variant_has_no_zero_quantity_movement() -> None:
    product = Product(name="Test", slug="test", description="Test", base_price_minor=100)

    variant = seed._variant(
        product,
        sku="TEST-0",
        display_name="Out of stock",
        stock=0,
    )

    assert variant.stock_on_hand == 0
    assert variant.movements == []
