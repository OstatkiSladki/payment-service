from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from schemas.promo import DiscountType


class PromoCodeCreateRequest(BaseModel):
    code: str = Field(max_length=50, pattern='^[A-Z0-9_-]+$')
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=Decimal('0.00'))
    min_order_amount: Decimal = Field(default=Decimal('0.00'), ge=Decimal('0.00'))
    valid_until: datetime | None = None
    max_usages_per_user: int | None = Field(default=None, ge=1)
    total_max_usages: int | None = Field(default=None, ge=1)
    rules_json: dict[str, Any] = Field(default_factory=dict)


class PromoCodeUpdateRequest(BaseModel):
    discount_value: Decimal | None = Field(default=None, gt=Decimal('0.00'))
    min_order_amount: Decimal | None = Field(default=None, ge=Decimal('0.00'))
    valid_until: datetime | None = None
    is_active: bool | None = None
    max_usages_per_user: int | None = Field(default=None, ge=1)
    total_max_usages: int | None = Field(default=None, ge=1)
    rules_json: dict[str, Any] | None = None


class PromoCodeResponse(BaseModel):
    id: str
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    min_order_amount: Decimal
    valid_until: datetime | None
    is_active: bool
    max_usages_per_user: int | None
    total_max_usages: int | None
    current_usages: int
    rules_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None
    created_by: str | None = None


class PromoUsageEntry(BaseModel):
    id: str
    user_id: str
    order_id: int | None
    payment_id: str | None
    discount_applied: Decimal
    created_at: datetime


class PromoCodeStatistics(BaseModel):
    promo_code_id: str
    code: str
    total_usages: int
    total_discount_amount: Decimal
    total_order_amount: Decimal
    unique_users: int
    usage_by_period: list[dict[str, Any]]
    recent_usages: list[PromoUsageEntry]
    conversion_rate: float


class OverviewStatistics(BaseModel):
    period: dict[str, date | None]
    payments: dict[str, int | Decimal]
    promo_codes: dict[str, int | Decimal]
    payment_methods: list[dict[str, int | Decimal | str]]
