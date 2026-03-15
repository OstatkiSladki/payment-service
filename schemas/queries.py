from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

from schemas.payment import PaymentStatus
from schemas.promo import DiscountType


class StatsPeriod(str, Enum):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    ALL = 'all'


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


def payment_list_query_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Annotated[PaymentStatus | None, Query()] = None,
    order_id: Annotated[int | None, Query(ge=1)] = None,
) -> PaymentListQuery:
    return PaymentListQuery(limit=limit, offset=offset, status=status, order_id=order_id)


def admin_promo_list_query_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_active: Annotated[bool | None, Query()] = None,
    discount_type: Annotated[DiscountType | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=50)] = None,
) -> AdminPromoListQuery:
    return AdminPromoListQuery(
        limit=limit,
        offset=offset,
        is_active=is_active,
        discount_type=discount_type,
        search=search,
    )


def promo_stats_query_params(
    period: Annotated[StatsPeriod, Query()] = StatsPeriod.ALL,
) -> PromoStatsQuery:
    return PromoStatsQuery(period=period)


def overview_stats_query_params(
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> OverviewStatsQuery:
    return OverviewStatsQuery(from_date=from_date, to_date=to_date)
