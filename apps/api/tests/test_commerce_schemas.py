from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from bukkystore_api.commerce.schemas import CheckoutRequest


def _checkout(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "customer": {
            "full_name": "Ada Okafor",
            "phone": "+2348012345678",
            "email": "ADA@example.com",
        },
        "delivery": {
            "area_id": str(uuid4()),
            "address": "12 Example Street, Lagos",
        },
        "items": [{"variant_id": str(uuid4()), "quantity": 2}],
    }
    payload.update(overrides)
    return payload


def test_checkout_schema_normalizes_customer_details() -> None:
    payload = _checkout(
        customer={
            "full_name": "  Ada Okafor  ",
            "phone": "+2348012345678",
            "email": "ADA@example.com",
        },
        attribution={"source": "  instagram  ", "campaign": "  launch  "},
    )
    checkout = CheckoutRequest.model_validate(payload)

    assert checkout.customer.email == "ada@example.com"
    assert checkout.customer.full_name == "Ada Okafor"
    assert checkout.attribution is not None
    assert checkout.attribution.source == "instagram"
    assert checkout.items[0].quantity == 2


def test_checkout_openapi_excludes_whitespace_shorter_than_normalized_minimum() -> None:
    schema = CheckoutRequest.model_json_schema()

    customer = schema["$defs"]["CheckoutCustomer"]
    assert customer["properties"]["full_name"]["pattern"] == r"^\S.*\S$"


@pytest.mark.parametrize("phone", ["080123", "+441234567890", "not-a-phone"])
def test_checkout_schema_rejects_non_nigerian_phone(phone: str) -> None:
    payload = _checkout()
    payload["customer"] = {"full_name": "Ada Okafor", "phone": phone}

    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_checkout_schema_rejects_duplicate_variants() -> None:
    variant_id = str(uuid4())

    with pytest.raises(ValidationError, match="only once"):
        CheckoutRequest.model_validate(
            _checkout(
                items=[
                    {"variant_id": variant_id, "quantity": 1},
                    {"variant_id": variant_id, "quantity": 2},
                ]
            )
        )


def test_checkout_schema_rejects_unknown_totals() -> None:
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(_checkout(total_minor=100))
