from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PaymentStatus(StrEnum):
  PENDING = "pending"
  SUCCEEDED = "succeeded"
  FAILED = "failed"
  REFUNDED = "refunded"
  PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(StrEnum):
  BANK_CARD = "bank_card"
  SBP = "sbp"


class PaymentCreateRequest(BaseModel):
  order_id: int = Field(ge=1)
  amount: Decimal = Field(gt=Decimal("0.00"))
  currency: str = Field(default="RUB", min_length=3, max_length=3)
  payment_method: PaymentMethod
  transaction_id: str = Field(min_length=1, max_length=255)
  promo_code: str | None = Field(default=None, max_length=50)
  meta: dict[str, Any] = Field(default_factory=dict)


class PaymentRefundRequest(BaseModel):
  reason: str | None = Field(default=None, max_length=500)


class PaymentResponse(BaseModel):
  id: str
  order_id: int
  transaction_id: str
  amount: Decimal
  refunded_amount: Decimal
  currency: str
  status: PaymentStatus
  payment_method: PaymentMethod | None
  promo_code_applied: str | None = None
  discount_amount: Decimal | None = None
  failure_reason: str | None = None
  created_at: datetime
  paid_at: datetime | None = None
  refunded_at: datetime | None = None
