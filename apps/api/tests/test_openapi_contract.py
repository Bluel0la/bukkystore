from __future__ import annotations

import schemathesis
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


@schema.parametrize()
def test_openapi_operations_do_not_violate_the_contract(case: Case) -> None:
    """Fuzz every documented operation and reject schema drift or unhandled errors."""

    case.call_and_validate()
