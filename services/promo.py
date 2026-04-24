from datetime import datetime, timezone
from decimal import Decimal

import grpc
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.promo_code import PromoCodeRepository
from repositories.promo_code_usage import PromoCodeUsageRepository
from schemas.promo import PromoValidateResponse
from services.errors import ServiceError
from services.grpc_clients import (
  CircuitBreakerOpenError,
  GrpcDependencyError,
  OrderServiceClient,
  VenueServiceClient,
)


class PromoService:
  def __init__(
    self,
    session: AsyncSession,
    *,
    order_client: OrderServiceClient,
    venue_client: VenueServiceClient,
  ):
    self.session = session
    self.repo = PromoCodeRepository(session)
    self.usage_repo = PromoCodeUsageRepository(session)
    self.order_client = order_client
    self.venue_client = venue_client

  async def validate_for_payment(
    self,
    code: str,
    order_amount: Decimal,
    user_id: int,
    request_id: str | None = None,
    order_details=None,
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

    required_venue_id = promo.venue_id or promo.rules_json.get("venue_id")
    if required_venue_id is not None:
      if order_details is None:
        raise ServiceError(400, "ORDER_CONTEXT_REQUIRED", "Order context is required", request_id)
      if int(order_details.venue_id) != int(required_venue_id):
        raise ServiceError(400, "PROMO_VENUE_MISMATCH", "Promo code is not valid for this venue", request_id)
      try:
        venue_validation = await self.venue_client.validate_venue(int(order_details.venue_id))
      except grpc.aio.AioRpcError as exc:
        raise ServiceError(
          503,
          "VENUE_SERVICE_UNAVAILABLE",
          "Venue service is unavailable",
          request_id,
        ) from exc
      except (GrpcDependencyError, CircuitBreakerOpenError) as exc:
        raise ServiceError(
          503,
          "VENUE_SERVICE_UNAVAILABLE",
          "Venue service is unavailable",
          request_id,
        ) from exc
      if not venue_validation.is_valid:
        raise ServiceError(400, "VENUE_INVALID", "Venue is not available for promo usage", request_id)

    if promo.discount_type == "percent":
      discount_amount = (order_amount * promo.discount_value) / Decimal("100")
    else:
      discount_amount = promo.discount_value

    if discount_amount > order_amount:
      discount_amount = order_amount

    usages_left = None
    if promo.max_usages_per_user is not None:
      usages_left = max(promo.max_usages_per_user - user_usages, 0)

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
