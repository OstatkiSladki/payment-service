from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class DiscountType(StrEnum):
  FIXED = "fixed"
  PERCENT = "percent"


class PromoValidateRequest(BaseModel):
  code: str = Field(max_length=50)
  order_amount: Decimal = Field(ge=Decimal("0.00"))


class PromoValidateResponse(BaseModel):
  is_valid: bool
  discount_type: DiscountType
  discount_value: Decimal
  discount_amount: Decimal
  final_amount: Decimal
  min_order_amount: Decimal
  valid_until: datetime | None = None
  usages_left: int | None = None


class PromoValidationError(BaseModel):
  is_valid: bool = False
  error_code: str
  message: str
  valid_until: datetime | None = None
