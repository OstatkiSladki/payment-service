from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
  field: str
  message: str


class ErrorResponse(BaseModel):
  code: str
  message: str
  details: list[ErrorDetail] | None = None
  request_id: str | None = None


class PaginatedResponse(BaseModel):
  items: list[Any]
  total: int
  offset: int
  limit: int


class HealthChecks(BaseModel):
  database: Literal["ok", "failed"]
  cache: Literal["ok", "failed"] | None = None


class HealthResponse(BaseModel):
  status: Literal["healthy", "unhealthy"]
  version: str
  timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  checks: HealthChecks
