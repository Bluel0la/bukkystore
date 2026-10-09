from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SessionId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    ),
]
Source = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50, pattern=r"^\S(?:.*\S)?$"),
]
Campaign = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=100, pattern=r"^\S(?:.*\S)?$"
    ),
]
MetadataKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
MetadataValue = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class AnalyticsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalyticsEventCreate(AnalyticsSchema):
    """One best-effort browsing/conversion event from the storefront."""

    event_type: str = Field(pattern=r"^(product_view|share_click|whatsapp_click)$")
    session_id: SessionId
    product_id: UUID | None = None
    source: Source | None = None
    campaign: Campaign | None = None
    metadata: dict[MetadataKey, MetadataValue] = Field(default_factory=dict, max_length=10)

    @field_validator("source", mode="before")
    @classmethod
    def default_source(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "direct"
        return value.lower().strip() if isinstance(value, str) else value


class AnalyticsEventResponse(AnalyticsSchema):
    id: UUID
    event_type: str
    created_at: datetime
