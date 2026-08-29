from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.auth import bootstrap
from bukkystore_api.auth.models import UserRole


async def test_first_bootstrap_user_must_be_owner() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=0)

    with pytest.raises(ValueError, match="first administrator"):
        await bootstrap.create_admin_user(
            session,
            email="admin@example.com",
            display_name="Admin",
            role=UserRole.ADMIN,
            password="correct-password-value",
        )


async def test_bootstrap_creates_normalized_owner() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=0)
    session.commit = AsyncMock()

    user = await bootstrap.create_admin_user(
        session,
        email="OWNER@EXAMPLE.COM",
        display_name=" Store Owner ",
        role=UserRole.OWNER,
        password="correct-password-value",
    )

    assert user.email == "owner@example.com"
    assert user.display_name == "Store Owner"
    assert user.password_hash != "correct-password-value"  # noqa: S105


async def test_bootstrap_maps_duplicate_email_to_safe_error() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=1)
    session.commit = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate")))
    session.rollback = AsyncMock()

    with pytest.raises(ValueError, match="already exists"):
        await bootstrap.create_admin_user(
            session,
            email="admin@example.com",
            display_name="Admin",
            role=UserRole.ADMIN,
            password="correct-password-value",
        )
    session.rollback.assert_awaited_once()


def test_bootstrap_main_rejects_password_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["bootstrap", "--email", "a@b.com", "--display-name", "A"])
    monkeypatch.setattr(bootstrap.getpass, "getpass", MagicMock(side_effect=["first", "second"]))

    with pytest.raises(SystemExit, match="Passwords do not match"):
        bootstrap.main()


def test_bootstrap_main_runs_validated_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["bootstrap", "--email", "owner@example.com", "--display-name", "Owner", "--role", "OWNER"],
    )
    monkeypatch.setattr(
        bootstrap.getpass,
        "getpass",
        MagicMock(side_effect=["correct-password-value", "correct-password-value"]),
    )
    run = AsyncMock()
    monkeypatch.setattr(bootstrap, "_run", run)

    bootstrap.main()

    run.assert_awaited_once()


async def test_run_uses_database_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock(spec=AsyncSession)

    class SessionFactory:
        @asynccontextmanager
        async def __call__(self) -> AsyncIterator[AsyncSession]:
            yield session

    database = SimpleNamespace(session_factory=SessionFactory(), dispose=AsyncMock())
    monkeypatch.setattr(bootstrap, "Database", lambda _url: database)
    monkeypatch.setattr(
        bootstrap,
        "get_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://unused"),
    )
    user = SimpleNamespace(role=UserRole.OWNER, email="owner@example.com")
    monkeypatch.setattr(bootstrap, "create_admin_user", AsyncMock(return_value=user))

    await bootstrap._run(
        SimpleNamespace(email=user.email, display_name="Owner", role="OWNER"),
        "correct-password-value",
    )

    database.dispose.assert_awaited_once()
