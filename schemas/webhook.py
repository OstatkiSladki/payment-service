from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from schemas.payment import PaymentStatus


class WebhookPayload(BaseModel):
  transaction_id: str
  status: PaymentStatus
  amount: Decimal
  currency: str
  paid_at: datetime | None = None


class WebhookResponse(BaseModel):
  status: str
