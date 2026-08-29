from __future__ import annotations

from httpx import AsyncClient


async def test_empty_public_catalogue_is_a_valid_response(client: AsyncClient) -> None:
    categories = await client.get("/api/v1/categories")
    products = await client.get("/api/v1/products")

    assert categories.status_code == 200
    assert categories.json() == []
    assert products.status_code == 200
    assert products.json() == {"items": [], "next_cursor": None}


async def test_product_detail_returns_safe_not_found_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products/not-in-catalogue")

    assert response.status_code == 404
    assert response.json()["code"] == "product_not_found"
    assert response.json()["message"] == "The requested product was not found."


async def test_invalid_cursor_returns_safe_client_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products", params={"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_cursor"


async def test_inverted_price_range_is_rejected(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/products", params={"min_price_minor": 20_000, "max_price_minor": 10_000}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_price_range"


async def test_unknown_filter_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products", params={"unexpected": "value"})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
