from __future__ import annotations

from httpx import AsyncClient

from bukkystore_api.auth.models import UserRole
from bukkystore_api.auth.schemas import AdminUserResponse, LoginResponse
from bukkystore_api.auth.service import IssuedSession


async def test_admin_catalogue_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/products")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


async def test_invalid_login_is_safe_and_sets_no_cookie(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "owner@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert "set-cookie" not in response.headers


async def test_login_rejects_unknown_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": "owner@example.com",
            "password": "incorrect-password",
            "role": "OWNER",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_valid_login_sets_secure_session_boundaries(
    client: AsyncClient, monkeypatch: object
) -> None:
    from datetime import UTC, datetime, timedelta
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from bukkystore_api.auth import router

    expires_at = datetime.now(UTC) + timedelta(hours=1)
    issued = IssuedSession(
        response=LoginResponse(
            user=AdminUserResponse(
                id=uuid4(),
                email="owner@example.com",
                display_name="Owner",
                role=UserRole.OWNER,
            ),
            expires_at=expires_at,
        ),
        session_token="session-token",
        csrf_token="csrf-token",
    )
    monkeypatch.setattr(router, "authenticate", AsyncMock(return_value=issued))  # type: ignore[attr-defined]

    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "owner@example.com", "password": "correct-password-value"},
    )

    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    assert any(
        "bukky_admin_session=session-token" in value and "HttpOnly" in value for value in cookies
    )
    assert any(
        "bukky_admin_csrf=csrf-token" in value and "HttpOnly" not in value for value in cookies
    )
