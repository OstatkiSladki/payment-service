from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel

from schemas.payment import PaymentStatus
from schemas.promo import DiscountType


class StatsPeriod(str, Enum):
  DAY = "day"
  WEEK = "week"
  MONTH = "month"
  ALL = "all"


class PaymentListQuery(BaseModel):
  limit: int = 20
  offset: int = 0
  status: PaymentStatus | None = None
  order_id: int | None = None


class AdminPromoListQuery(BaseModel):
  limit: int = 20
  offset: int = 0
  is_active: bool | None = None
  discount_type: DiscountType | None = None
  search: str | None = None


class PromoStatsQuery(BaseModel):
  period: StatsPeriod = StatsPeriod.ALL


class OverviewStatsQuery(BaseModel):
  from_date: date | None = None
  to_date: date | None = None
