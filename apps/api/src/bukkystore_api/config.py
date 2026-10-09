from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated process configuration loaded once at application startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        # A repository-level dotenv also serves Docker and Next.js. Ignore keys
        # outside this typed APP_ namespace instead of reflecting their values in
        # a startup validation error.
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: PostgresDsn
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)
    public_site_url: AnyHttpUrl = Field(default_factory=lambda: AnyHttpUrl("http://localhost:3000"))
    session_secret: SecretStr = Field(min_length=32)
    payment_provider: Literal["fake", "opay"] = "fake"
    cloudinary_cloud_name: str | None = Field(
        default=None, min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$"
    )
    cloudinary_api_key: SecretStr | None = Field(default=None, min_length=1, max_length=255)
    cloudinary_api_secret: SecretStr | None = Field(default=None, min_length=8, max_length=255)
    reservation_minutes: int = Field(default=15, ge=5, le=30)
    admin_session_hours: int = Field(default=12, ge=1, le=168)
    admin_login_window_minutes: int = Field(default=15, ge=5, le=60)
    admin_login_max_failures: int = Field(default=5, ge=3, le=20)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_driver(cls, value: object) -> object:
        if isinstance(value, str):
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+asyncpg://", 1)
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @model_validator(mode="after")
    def enforce_production_safety(self) -> Self:
        cloudinary_values = (
            self.cloudinary_cloud_name,
            self.cloudinary_api_key,
            self.cloudinary_api_secret,
        )
        if any(cloudinary_values) and not all(cloudinary_values):
            raise ValueError(
                "Cloudinary configuration must include cloud name, API key, and secret"
            )
        if self.environment == "production" and self.payment_provider == "fake":
            raise ValueError("The fake payment provider is forbidden in production")
        if self.environment == "production" and not self.cors_origins:
            raise ValueError("At least one explicit CORS origin is required in production")
        if self.environment == "production" and not all(cloudinary_values):
            raise ValueError("Cloudinary configuration is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the immutable application settings singleton."""

    return Settings()
