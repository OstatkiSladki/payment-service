from typing import Literal

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import WebhookSignatureVerifier
from dependency import get_db_session
from models.payment import PaymentStatus
from repositories.payment import PaymentRepository
from schemas.webhook import WebhookPayload, WebhookResponse

router = APIRouter()


@router.post("/{gateway}", response_model=WebhookResponse)
async def receive_webhook(
  gateway: Literal["bank_card", "sbp"],
  request: Request,
  x_gateway_signature: str | None = Header(default=None, alias="X-Gateway-Signature"),
  session: AsyncSession = Depends(get_db_session),
) -> WebhookResponse:
  verifier = WebhookSignatureVerifier()
  raw_body = await request.body()
  verifier.verify(raw_body, x_gateway_signature)

  payload = WebhookPayload.model_validate_json(raw_body)
  payment_repo = PaymentRepository(session)
  payment = await payment_repo.get_by_transaction_id(payload.transaction_id)

  if payment is None:
    # TODO: persist orphan webhook payloads for async reconciliation with external gateway IDs.
    return WebhookResponse(status="accepted")

  payment.status = PaymentStatus(payload.status.value)
  if payload.paid_at is not None:
    payment.paid_at = payload.paid_at
  await payment_repo.save(payment)
  await session.commit()

  # TODO: publish payment status update event once notification contracts are implemented.
  # TODO: map gateway-specific signatures and payload formats per provider.
  return WebhookResponse(status="accepted")
