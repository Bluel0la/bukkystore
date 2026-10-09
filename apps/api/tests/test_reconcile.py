from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from bukkystore_api.commerce import reconcile


class FakeDatabase:
    def __init__(self) -> None:
        self.session = object()
        self.disposed = False

    @asynccontextmanager
    async def session_factory(self) -> Any:
        yield self.session

    async def dispose(self) -> None:
        self.disposed = True


async def test_reconcile_run_expires_one_batch_and_disposes(monkeypatch: Any) -> None:
    database = FakeDatabase()
    expire = AsyncMock(return_value=3)
    monkeypatch.setattr(reconcile, "Database", lambda _url: database)
    monkeypatch.setattr(
        reconcile, "get_settings", lambda: SimpleNamespace(database_url="postgresql://unused")
    )
    monkeypatch.setattr(reconcile, "expire_reservations", expire)

    assert await reconcile._run() == 3
    expire.assert_awaited_once_with(database.session)
    assert database.disposed is True


def test_reconcile_main_reports_count(monkeypatch: Any, capsys: Any) -> None:
    async def run() -> int:
        return 2

    monkeypatch.setattr(reconcile, "_run", run)

    reconcile.main()

    assert capsys.readouterr().out.strip() == "Expired reservations: 2"
