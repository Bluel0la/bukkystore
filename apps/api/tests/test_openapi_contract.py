from __future__ import annotations

import schemathesis
from hypothesis import settings
from schemathesis import Case

from bukkystore_api.config import Settings
from bukkystore_api.main import create_app
from tests.conftest import FakeDatabase

contract_settings = Settings(
    environment="test",
    database_url="postgresql+asyncpg://test:test@localhost:5432/test",
    cors_origins=["http://localhost:3000"],
    session_secret="contract-test-secret-with-at-least-32-characters",
    payment_provider="fake",
)
contract_app = create_app(contract_settings, FakeDatabase())
schema = schemathesis.openapi.from_asgi("/api/openapi.json", contract_app)


@schema.exclude(path="/api/v1/products").parametrize()
def test_openapi_operations_do_not_violate_the_contract(case: Case) -> None:
    """Fuzz every documented operation and reject schema drift or unhandled errors."""

    case.call_and_validate()


@schema.include(path="/api/v1/products").parametrize()
@settings(max_examples=25)
def test_product_listing_fuzzes_schema_valid_semantic_filters(case: Case) -> None:
    """Fuzz product filters after normalizing cross-field and opaque cursor semantics."""

    if case.query is not None:
        for key in (
            "category",
            "search",
            "size",
            "available",
            "featured",
            "min_price_minor",
            "max_price_minor",
        ):
            if case.query.get(key) in (None, "null"):
                case.query.pop(key, None)
        case.query.pop("cursor", None)
        minimum = case.query.get("min_price_minor")
        maximum = case.query.get("max_price_minor")
        if minimum is not None and maximum is not None:
            try:
                minimum_value = int(minimum)
                maximum_value = int(maximum)
            except (TypeError, ValueError):
                pass
            else:
                if minimum_value > maximum_value:
                    case.query["min_price_minor"] = maximum_value
                    case.query["max_price_minor"] = minimum_value
    case.call_and_validate()
