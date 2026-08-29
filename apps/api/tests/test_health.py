from __future__ import annotations

from uuid import UUID

from httpx import AsyncClient

from tests.conftest import FakeDatabase


async def test_liveness_returns_version_and_request_metadata(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "bukkystore-api",
        "version": "0.1.0",
    }
    UUID(response.headers["x-request-id"])
    assert response.headers["server-timing"].startswith("app;dur=")


async def test_valid_request_id_is_propagated(client: AsyncClient) -> None:
    request_id = "7c98e7aa-084a-4f97-81c6-5337c1bfc5b4"

    response = await client.get("/api/v1/health/live", headers={"X-Request-ID": request_id})

    assert response.headers["x-request-id"] == request_id


async def test_invalid_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live", headers={"X-Request-ID": "not-safe-for-logs"}
    )

    assert response.headers["x-request-id"] != "not-safe-for-logs"
    UUID(response.headers["x-request-id"])


async def test_readiness_reports_available_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "available"}


async def test_readiness_fails_securely(client: AsyncClient, fake_database: FakeDatabase) -> None:
    fake_database.ready = False

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "service_not_ready"
    assert payload["message"] == "A required service is unavailable."
    assert "database" not in str(payload).lower()
