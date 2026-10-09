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
        "cloudinary_cloud_name": "bukky-test",
        "cloudinary_api_key": "cloudinary-key",
        "cloudinary_api_secret": "cloudinary-secret",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_production_rejects_fake_payment_provider() -> None:
    with pytest.raises(ValidationError, match="fake payment provider"):
        production_settings(payment_provider="fake")


def test_production_requires_explicit_cors_origin() -> None:
    with pytest.raises(ValidationError, match="CORS origin"):
        production_settings(cors_origins=[])


def test_cloudinary_configuration_is_all_or_nothing_and_required_in_production() -> None:
    with pytest.raises(ValidationError, match="must include"):
        production_settings(cloudinary_api_secret=None)

    with pytest.raises(ValidationError, match="required in production"):
        production_settings(
            cloudinary_cloud_name=None,
            cloudinary_api_key=None,
            cloudinary_api_secret=None,
        )


def test_reservation_duration_has_safe_bounds() -> None:
    with pytest.raises(ValidationError):
        production_settings(reservation_minutes=2)


def test_unrelated_process_configuration_is_ignored() -> None:
    settings = production_settings(unrelated_service_secret="must-not-be-reflected")

    assert not hasattr(settings, "unrelated_service_secret")


@pytest.mark.parametrize("scheme", ["postgresql://", "postgres://"])
def test_provider_database_urls_use_the_async_driver(scheme: str) -> None:
    settings = production_settings(database_url=f"{scheme}test:test@localhost:5432/test")

    assert str(settings.database_url).startswith("postgresql+asyncpg://")
