from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from bukkystore_api.auth.dependencies import AdminContext, require_csrf
from bukkystore_api.auth.models import AdminSession, AdminUser, UserRole
from bukkystore_api.auth.security import hash_token
from bukkystore_api.config import Settings
from bukkystore_api.errors import ApiError


def _context_and_settings() -> tuple[AdminContext, Settings, str]:
    settings = Settings(
        environment="test",
        database_url="postgresql+asyncpg://test:test@localhost/test",
        session_secret="test-secret-value-with-at-least-32-characters",
    )
    token = "csrf-token"  # noqa: S105
    user = AdminUser(
        id=uuid4(),
        email="owner@example.com",
        password_hash="unused",
        display_name="Owner",
        role=UserRole.OWNER,
        is_active=True,
    )
    record = AdminSession(
        user=user,
        token_hash="a" * 64,
        csrf_token_hash=hash_token(token, settings.session_secret.get_secret_value()),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    return AdminContext(user=user, session=record), settings, token


async def test_csrf_accepts_cookie_header_and_session_binding() -> None:
    context, settings, token = _context_and_settings()
    assert await require_csrf(context, settings, token, token) is context


@pytest.mark.parametrize(
    ("cookie", "header"),
    [(None, None), ("cookie", "header"), ("wrong", "wrong")],
)
async def test_csrf_fails_securely(cookie: str | None, header: str | None) -> None:
    context, settings, _token = _context_and_settings()
    with pytest.raises(ApiError) as error:
        await require_csrf(context, settings, cookie, header)
    assert error.value.status_code == 403
