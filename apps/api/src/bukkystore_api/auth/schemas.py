from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from bukkystore_api.auth.models import UserRole

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=254,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    ),
]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class AuthSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(AuthSchema):
    email: Email
    password: Password

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class AdminUserResponse(AuthSchema):
    id: UUID
    email: str
    display_name: str
    role: UserRole


class LoginResponse(AuthSchema):
    user: AdminUserResponse
    expires_at: datetime
