from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictResponseModel):
    status: Literal["ok"]
    service: Literal["bukkystore-api"] = "bukkystore-api"
    version: str


class ReadinessResponse(StrictResponseModel):
    status: Literal["ready"]
    database: Literal["available"]


class ErrorResponse(StrictResponseModel):
    code: str
    message: str
    correlation_id: str
