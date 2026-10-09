from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import AsyncClient

from bukkystore_api.auth.dependencies import require_admin, require_csrf
from bukkystore_api.auth.models import UserRole
from bukkystore_api.auth.schemas import AdminUserResponse, LoginResponse
from bukkystore_api.auth.service import IssuedSession


async def test_admin_catalogue_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/products")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


async def test_product_archive_routes_require_authentication(client: AsyncClient) -> None:
    product_id = str(uuid4())
    archive = await client.post(f"/api/v1/admin/products/{product_id}/archive")
    unarchive = await client.post(f"/api/v1/admin/products/{product_id}/unarchive")
    bulk = await client.post(
        "/api/v1/admin/products/bulk-archive",
        json={"product_ids": [product_id], "archived": True},
    )

    for response in (archive, unarchive, bulk):
        assert response.status_code == 401
        assert response.json()["code"] == "authentication_required"


def _archived_product_payload(product_id: object) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(product_id),
        "category": {"id": str(uuid4()), "name": "Dresses", "slug": "dresses", "parent_id": None},
        "name": "Brown Dress",
        "slug": "brown-dress",
        "description": "A dress",
        "base_price_minor": 2_500_000,
        "compare_at_price_minor": None,
        "currency": "NGN",
        "status": "ARCHIVED",
        "featured": False,
        "variants": [],
        "images": [],
        "created_at": now,
        "updated_at": now,
    }


async def test_product_archive_routes_execute_with_authentication(
    client: AsyncClient, app: Any, monkeypatch: Any
) -> None:
    from types import SimpleNamespace

    from bukkystore_api.admin_catalogue import router as catalogue_router
    from bukkystore_api.admin_catalogue.schemas import AdminProductResponse

    product_id = uuid4()
    archived = AdminProductResponse.model_validate(_archived_product_payload(product_id))
    monkeypatch.setattr(catalogue_router, "archive_product", AsyncMock(return_value=archived))
    monkeypatch.setattr(catalogue_router, "unarchive_product", AsyncMock(return_value=archived))
    monkeypatch.setattr(catalogue_router, "bulk_set_archived", AsyncMock(return_value=[product_id]))
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace()
    app.dependency_overrides[require_csrf] = lambda: SimpleNamespace()

    archive = await client.post(f"/api/v1/admin/products/{product_id}/archive")
    unarchive = await client.post(f"/api/v1/admin/products/{product_id}/unarchive")
    bulk = await client.post(
        "/api/v1/admin/products/bulk-archive",
        json={"product_ids": [str(product_id)], "archived": True},
    )

    assert archive.status_code == 200
    assert archive.json()["status"] == "ARCHIVED"
    assert unarchive.status_code == 200
    assert bulk.status_code == 200
    assert bulk.json() == {"archived": True, "product_ids": [str(product_id)]}


async def test_admin_orders_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/orders")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


async def test_admin_analytics_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/analytics/overview")

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
