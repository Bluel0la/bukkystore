from __future__ import annotations

import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis import Case
from schemathesis.specs.openapi.checks import missing_required_header

from bukkystore_api.config import Settings
from bukkystore_api.main import create_app
from tests.conftest import FakeDatabase

contract_settings = Settings(
    environment="test",
    database_url="postgresql+asyncpg://test:test@localhost:5432/test",
    cors_origins=["http://localhost:3000"],
    session_secret="contract-test-secret-with-at-least-32-characters",
    payment_provider="fake",
    log_level="ERROR",
)
contract_app = create_app(contract_settings, FakeDatabase())
schema = schemathesis.openapi.from_asgi("/api/openapi.json", contract_app)


@schema.exclude(path="/api/v1/products").exclude(path="/api/v1/admin/auth/login").parametrize()
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much],
)
def test_openapi_operations_do_not_violate_the_contract(case: Case) -> None:
    """Fuzz every documented operation and reject schema drift or unhandled errors."""

    protected_header_paths = {
        "/api/v1/admin/variants/{variant_id}/stock-adjustments": "contract-test-key",
        "/api/v1/admin/orders/{order_id}/transitions": "contract-order-transition-key",
        "/api/v1/admin/orders/{order_id}/cancellations": "contract-order-cancellation-key",
        "/api/v1/admin/refunds/{refund_id}/complete": "contract-refund-completion-key",
        "/api/v1/checkout": "contract-checkout-key",
    }
    if case.operation.path in protected_header_paths:
        if case.headers is None:
            case.headers = {}
        case.headers.setdefault("Idempotency-Key", protected_header_paths[case.operation.path])
        # FastAPI reports missing required headers with its documented 422
        # validation response; Schemathesis currently expects 406 for this check.
        case.call_and_validate(excluded_checks=[missing_required_header])
        return
    case.call_and_validate()


@schema.include(path="/api/v1/admin/auth/login").parametrize()
@settings(
    max_examples=3,
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much],
)
def test_login_contract_with_bounded_password_hash_work(case: Case) -> None:
    """Fuzz sign-in while bounding intentionally expensive password verification."""

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
