from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependency import CurrentUser, get_current_user, get_db_session
from schemas.promo import PromoValidateRequest, PromoValidateResponse
from services.promo import PromoService

router = APIRouter()


@router.post('/validate', response_model=PromoValidateResponse)
async def validate_promo(
    payload: PromoValidateRequest,
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PromoValidateResponse:
    service = PromoService(session)
    return await service.validate_for_payment(
        code=payload.code,
        order_amount=payload.order_amount,
        user_id=actor.user_id,
        request_id=actor.request_id,
    )
