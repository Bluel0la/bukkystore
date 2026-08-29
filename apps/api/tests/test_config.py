from __future__ import annotations

import pytest
from pydantic import ValidationError

from bukkystore_api.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "production",
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/test",
        "cors_origins": ["https://bukkystore.example"],
        "session_secret": "production-secret-value-with-at-least-32-characters",
        "payment_provider": "opay",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_production_rejects_fake_payment_provider() -> None:
    with pytest.raises(ValidationError, match="fake payment provider"):
        production_settings(payment_provider="fake")


def test_production_requires_explicit_cors_origin() -> None:
    with pytest.raises(ValidationError, match="CORS origin"):
        production_settings(cors_origins=[])


def test_reservation_duration_has_safe_bounds() -> None:
    with pytest.raises(ValidationError):
        production_settings(reservation_minutes=2)
