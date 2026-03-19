from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.promo_code import PromoCodeRepository
from repositories.promo_code_usage import PromoCodeUsageRepository
from schemas.promo import PromoValidateResponse
from services.errors import ServiceError


class PromoService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = PromoCodeRepository(session)
    self.usage_repo = PromoCodeUsageRepository(session)

  async def validate_for_payment(
    self,
    code: str,
    order_amount: Decimal,
    user_id: int,
    request_id: str | None = None,
  ) -> PromoValidateResponse:
    promo = await self.repo.get_by_code(code)
    if promo is None:
      raise ServiceError(404, "PROMO_NOT_FOUND", "Promo code not found", request_id)
    if not promo.is_active:
      raise ServiceError(400, "PROMO_INACTIVE", "Promo code is inactive", request_id)
    if promo.valid_until and promo.valid_until < datetime.now(timezone.utc):
      raise ServiceError(400, "PROMO_EXPIRED", "Promo code is expired", request_id)
    if order_amount < promo.min_order_amount:
      raise ServiceError(400, "MIN_ORDER_NOT_MET", "Minimum order amount is not met", request_id)

    user_usages = await self.usage_repo.count_for_user(promo.id, user_id)
    if promo.max_usages_per_user is not None and user_usages >= promo.max_usages_per_user:
      raise ServiceError(400, "USER_LIMIT_REACHED", "User usage limit reached", request_id)

    total_usages = await self.usage_repo.count_total(promo.id)
    if promo.total_max_usages is not None and total_usages >= promo.total_max_usages:
      raise ServiceError(400, "MAX_USAGES_REACHED", "Promo total usage limit reached", request_id)

    if promo.discount_type == "percent":
      discount_amount = (order_amount * promo.discount_value) / Decimal("100")
    else:
      discount_amount = promo.discount_value

    if discount_amount > order_amount:
      discount_amount = order_amount

    usages_left = None
    if promo.max_usages_per_user is not None:
      usages_left = max(promo.max_usages_per_user - user_usages, 0)

    # TODO: enforce VenueService/category/first-order promo rules from rules_json after gRPC integration.
    return PromoValidateResponse(
      is_valid=True,
      discount_type=promo.discount_type,
      discount_value=promo.discount_value,
      discount_amount=discount_amount,
      final_amount=order_amount - discount_amount,
      min_order_amount=promo.min_order_amount,
      valid_until=promo.valid_until,
      usages_left=usages_left,
    )
