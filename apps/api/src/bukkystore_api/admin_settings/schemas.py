from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Phone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^(?:\+234|0)[789]\d{9}$"),
]
StoreName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=120, pattern=r"^\S.*\S$"),
]
HttpsUrl = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=10, max_length=500, pattern=r"^https://\S+$"
    ),
]
CurrencyCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$")]
HourOfDay = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^([01]\d|2[0-3]):[0-5]\d$"),
]


class SettingsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DaySchedule(SettingsSchema):
    """Opening hours for one weekday; either closed or an open/close pair."""

    closed: bool = False
    open: HourOfDay | None = "09:00"
    close: HourOfDay | None = "18:00"

    @model_validator(mode="after")
    def check_open_days_have_hours(self) -> DaySchedule:
        if self.closed:
            return self
        if self.open is None or self.close is None:
            raise ValueError("Open days require both open and close times")
        if self.open >= self.close:
            raise ValueError("Opening time must be before closing time")
        return self


class BusinessHours(SettingsSchema):
    monday: DaySchedule = Field(default_factory=DaySchedule)
    tuesday: DaySchedule = Field(default_factory=DaySchedule)
    wednesday: DaySchedule = Field(default_factory=DaySchedule)
    thursday: DaySchedule = Field(default_factory=DaySchedule)
    friday: DaySchedule = Field(default_factory=DaySchedule)
    saturday: DaySchedule = Field(default_factory=DaySchedule)
    sunday: DaySchedule = Field(default_factory=lambda: DaySchedule(closed=True))


class StoreSettingResponse(SettingsSchema):
    """Full business configuration; contains no secrets."""

    id: UUID
    store_name: str
    logo_ref: str | None
    whatsapp_number: str
    phone_number: str
    instagram_url: str | None
    tiktok_url: str | None
    address: str
    city: str
    currency: str
    minimum_order_minor: int | None
    business_hours: BusinessHours
    created_at: datetime
    updated_at: datetime


class PublicStoreSettingResponse(SettingsSchema):
    """Safe storefront-facing subset of the business configuration."""

    store_name: str
    logo_ref: str | None
    whatsapp_number: str
    phone_number: str
    instagram_url: str | None
    tiktok_url: str | None
    address: str
    city: str
    currency: str
    minimum_order_minor: int | None
    business_hours: BusinessHours


class StoreSettingUpdate(SettingsSchema):
    """Full-replace business configuration submitted from the admin form."""

    store_name: StoreName
    logo_ref: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        | None
    ) = None
    whatsapp_number: Phone
    phone_number: Phone
    instagram_url: HttpsUrl | None = None
    tiktok_url: HttpsUrl | None = None
    address: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=3, max_length=500, pattern=r"^\S.{1,}\S$"
        ),
    ]
    city: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=120, pattern=r"^\S.*\S$"),
    ] = "Lagos"
    currency: CurrencyCode = "NGN"
    minimum_order_minor: int | None = Field(default=None, ge=0)
    business_hours: BusinessHours = Field(default_factory=BusinessHours)


class AdminDeliveryAreaResponse(SettingsSchema):
    id: UUID
    name: str
    fee_minor: int
    currency: str
    display_position: int
    is_active: bool


class AdminDeliveryAreaCreate(SettingsSchema):
    name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=120, pattern=r"^\S.*\S$"),
    ]
    fee_minor: int = Field(ge=0)
    currency: CurrencyCode = "NGN"
    display_position: int = Field(default=0, ge=0)
    is_active: bool = True


class AdminDeliveryAreaUpdate(SettingsSchema):
    name: (
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True, min_length=2, max_length=120, pattern=r"^\S.*\S$"
            ),
        ]
        | None
    ) = None
    fee_minor: int | None = Field(default=None, ge=0)
    currency: CurrencyCode | None = None
    display_position: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
