from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bukkystore_api.auth.models import AdminSession, AdminUser, UserRole
from bukkystore_api.auth.security import hash_password
from bukkystore_api.auth.service import authenticate, resolve_session, revoke_session
from bukkystore_api.config import Settings
from bukkystore_api.errors import ApiError


def _settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://test:test@localhost/test",
        session_secret="test-secret-value-with-at-least-32-characters",
    )


def _user(*, active: bool = True) -> AdminUser:
    return AdminUser(
        id=uuid4(),
        email="owner@example.com",
        display_name="Owner",
        role=UserRole.OWNER,
        is_active=active,
        password_hash=hash_password("correct-password-value"),
    )


async def test_authenticate_creates_hashed_session() -> None:
    user = _user()
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(side_effect=[0, user])
    session.commit = AsyncMock()

    issued = await authenticate(
        session,
        _settings(),
        email=user.email,
        password="correct-password-value",
        network_identifier="127.0.0.1",
    )

    assert issued.response.user.id == user.id
    assert issued.session_token
    assert issued.csrf_token
    added = [call.args[0] for call in session.add.call_args_list]
    stored_session = next(item for item in added if isinstance(item, AdminSession))
    assert issued.session_token not in stored_session.token_hash
    session.commit.assert_awaited_once()


async def test_authenticate_records_failure_and_uses_safe_message() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(side_effect=[0, None])
    session.commit = AsyncMock()

    with pytest.raises(ApiError, match="Email or password") as error:
        await authenticate(
            session,
            _settings(),
            email="missing@example.com",
            password="incorrect-password",
            network_identifier="127.0.0.1",
        )

    assert error.value.status_code == 401
    session.commit.assert_awaited_once()


async def test_authenticate_throttles_repeated_failures() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=5)

    with pytest.raises(ApiError) as error:
        await authenticate(
            session,
            _settings(),
            email="owner@example.com",
            password="incorrect-password",
            network_identifier="127.0.0.1",
        )

    assert error.value.status_code == 429
    session.add.assert_not_called()


async def test_resolve_and_revoke_active_session() -> None:
    user = _user()
    record = AdminSession(
        id=uuid4(),
        user=user,
        token_hash="a" * 64,
        csrf_token_hash="b" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=record)
    session.commit = AsyncMock()

    assert await resolve_session(session, _settings(), "raw-token") is record
    assert await resolve_session(session, _settings(), None) is None
    await revoke_session(session, record)

    assert record.revoked_at is not None
    session.commit.assert_awaited_once()


async def test_resolve_rejects_inactive_user() -> None:
    record = AdminSession(
        user=_user(active=False),
        token_hash="a" * 64,
        csrf_token_hash="b" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=record)

    assert await resolve_session(session, _settings(), "raw-token") is None
