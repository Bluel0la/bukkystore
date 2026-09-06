from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient


def _payload() -> dict[str, object]:
    return {
        "customer": {"full_name": "Ada Okafor", "phone": "08012345678"},
        "delivery": {
            "area_id": str(uuid4()),
            "address": "12 Example Street, Lagos",
        },
        "items": [{"variant_id": str(uuid4()), "quantity": 1}],
    }


async def test_delivery_area_list_has_strict_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/delivery-areas")

    assert response.status_code == 200
    assert response.json() == []


async def test_checkout_requires_idempotency_key(client: AsyncClient) -> None:
    response = await client.post("/api/v1/checkout", json=_payload())

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_checkout_rejects_client_totals_and_missing_delivery_area(
    client: AsyncClient,
) -> None:
    payload = _payload()
    payload["total_minor"] = 1
    invalid = await client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "checkout-api-test-0001"},
        json=payload,
    )
    missing_area = await client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "checkout-api-test-0002"},
        json=_payload(),
    )

    assert invalid.status_code == 422
    assert missing_area.status_code == 404
    assert missing_area.json()["code"] == "delivery_area_not_found"


async def test_checkout_masks_malformed_json(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/checkout",
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": "checkout-api-test-0003",
        },
        content="{",
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_undecodable_body_uses_the_documented_validation_shape(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/analytics/events",
        headers={"Content-Type": "application/json"},
        content=b"\xed\xa0\x80",
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_guest_payment_status_does_not_reveal_unknown_orders(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/orders/BS-20260829-MISSING/payment-status",
        params={"token": "x" * 32},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "order_not_found"


async def test_fake_confirmation_requires_strict_private_order_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/payments/fake/confirm",
        json={"order_number": "BS-20260829-UNKNOWN", "order_access_token": "x" * 32, "amount": 1},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
