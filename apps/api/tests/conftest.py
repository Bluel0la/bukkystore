from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bukkystore_api.config import Settings
from bukkystore_api.main import create_app


class FakeDatabase:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
        self.disposed = False

    async def is_ready(self) -> bool:
        if not self.ready:
            raise OSError("database unavailable")
        return True

    async def dispose(self) -> None:
        self.disposed = True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        cors_origins=["http://localhost:3000"],
        session_secret="test-secret-value-with-at-least-32-characters",
        payment_provider="fake",
    )


@pytest.fixture
def fake_database() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def app(settings: Settings, fake_database: FakeDatabase) -> FastAPI:
    return create_app(settings, fake_database)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as test_client:
            yield test_client


@pytest.fixture(autouse=True)
def reset_logging() -> Iterator[None]:
    yield
