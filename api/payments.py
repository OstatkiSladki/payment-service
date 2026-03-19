from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependency import CurrentUser, get_current_user, get_db_session
from schemas.common import PaginatedResponse
from schemas.payment import PaymentCreateRequest, PaymentRefundRequest, PaymentResponse
from schemas.queries import PaymentListQuery
from services.payment import PaymentService

router = APIRouter()


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
  payload: PaymentCreateRequest,
  response: Response,
  actor: CurrentUser = Depends(get_current_user),
  session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
  service = PaymentService(session)
  result, status_code = await service.create_payment(payload, actor)
  response.status_code = status_code
  return result


@router.get("", response_model=PaginatedResponse)
async def list_user_payments(
  query: Annotated[PaymentListQuery, Query()],
  actor: CurrentUser = Depends(get_current_user),
  session: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
  service = PaymentService(session)
  items, total = await service.list_payments(
    actor=actor,
    limit=query.limit,
    offset=query.offset,
    status=query.status,
    order_id=query.order_id,
  )
  return PaginatedResponse(items=items, total=total, offset=query.offset, limit=query.limit)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
  payment_id: int,
  actor: CurrentUser = Depends(get_current_user),
  session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
  service = PaymentService(session)
  return await service.get_payment(payment_id, actor)


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
  payment_id: int,
  _: PaymentRefundRequest | None = None,
  actor: CurrentUser = Depends(get_current_user),
  session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
  service = PaymentService(session)
  return await service.refund_payment(payment_id, actor)
