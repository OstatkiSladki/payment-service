from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from dependency import CurrentUser
from models.promo_code import PromoCode
from repositories.payment import PaymentRepository
from repositories.promo_code import PromoCodeRepository
from repositories.promo_code_usage import PromoCodeUsageRepository
from schemas.admin import (
  OverviewStatistics,
  OverviewPeriod,
  PromoCodesOverviewStatistics,
  PromoCodeCreateRequest,
  PromoCodePatchRequest,
  PromoCodeResponse,
  PromoCodeStatistics,
  PromoUsageEntry,
)
from schemas.auth import UsersRole
from schemas.queries import StatsPeriod
from services.errors import ServiceError


class AdminService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.payment_repo = PaymentRepository(session)
    self.promo_repo = PromoCodeRepository(session)
    self.usage_repo = PromoCodeUsageRepository(session)

  @staticmethod
  def _assert_admin_role(actor: CurrentUser) -> None:
    if actor.role != UsersRole.ADMIN:
      raise ServiceError(403, "FORBIDDEN", "Admin access required", actor.request_id)

  async def create_promo(
    self, payload: PromoCodeCreateRequest, actor: CurrentUser
  ) -> PromoCodeResponse:
    self._assert_admin_role(actor)

    existing = await self.promo_repo.get_by_code(payload.code)
    if existing:
      raise ServiceError(409, "ALREADY_EXISTS", "Promo code already exists", actor.request_id)

    promo = PromoCode(
      code=payload.code,
      discount_type=payload.discount_type.value,
      discount_value=payload.discount_value,
      min_order_amount=payload.min_order_amount,
      valid_until=payload.valid_until,
      is_active=True,
      max_usages_per_user=payload.max_usages_per_user,
      total_max_usages=payload.total_max_usages,
      rules_json=payload.rules_json,
      venue_id=None,
    )
    await self.promo_repo.add(promo)
    await self.session.commit()
    await self.session.refresh(promo)
    return await self._to_response(promo)

  async def list_promos(
    self,
    actor: CurrentUser,
    limit: int,
    offset: int,
    is_active: bool | None,
    discount_type: str | None,
    search: str | None,
  ) -> tuple[list[PromoCodeResponse], int]:
    self._assert_admin_role(actor)
    rows, total = await self.promo_repo.list_for_admin(
      limit=limit,
      offset=offset,
      is_active=is_active,
      discount_type=discount_type,
      search=search,
    )
    return [await self._to_response(item) for item in rows], total

  async def get_promo(self, promo_id: int, actor: CurrentUser) -> PromoCodeResponse:
    self._assert_admin_role(actor)
    promo = await self.promo_repo.get_for_admin(promo_id)
    if promo is None:
      raise ServiceError(404, "NOT_FOUND", "Promo code not found", actor.request_id)
    return await self._to_response(promo)

  async def update_promo(
    self, promo_id: int, payload: PromoCodePatchRequest, actor: CurrentUser
  ) -> PromoCodeResponse:
    self._assert_admin_role(actor)
    promo = await self.promo_repo.get_for_admin(promo_id)
    if promo is None:
      raise ServiceError(404, "NOT_FOUND", "Promo code not found", actor.request_id)

    for field in payload.model_fields_set:
      setattr(promo, field, getattr(payload, field))

    await self.promo_repo.save(promo)
    await self.session.commit()
    await self.session.refresh(promo)
    return await self._to_response(promo)

  async def delete_promo(self, promo_id: int, actor: CurrentUser) -> None:
    self._assert_admin_role(actor)
    promo = await self.promo_repo.get_for_admin(promo_id)
    if promo is None:
      raise ServiceError(404, "NOT_FOUND", "Promo code not found", actor.request_id)
    promo.is_active = False
    await self.promo_repo.save(promo)
    await self.session.commit()

  async def promo_statistics(
    self, promo_id: int, period: StatsPeriod, actor: CurrentUser
  ) -> PromoCodeStatistics:
    self._assert_admin_role(actor)
    promo = await self.promo_repo.get_for_admin(promo_id)
    if promo is None:
      raise ServiceError(404, "NOT_FOUND", "Promo code not found", actor.request_id)

    total_usages = await self.usage_repo.count_total(promo_id)
    total_discount = await self.usage_repo.sum_discount(promo_id)
    unique_users = await self.usage_repo.count_unique_users(promo_id)
    usage_by_period = await self.usage_repo.usage_by_period(promo_id, period)
    recent_rows = await self.usage_repo.recent_entries(promo_id)
    total_order_amount = await self.payment_repo.sum_amount_for_promo(promo_id)

    recent_usages = [
      PromoUsageEntry(
        id=str(item.id),
        user_id=str(item.user_id),
        order_id=item.order_id,
        payment_id=str(item.payment_id) if item.payment_id is not None else None,
        discount_applied=item.discount_applied,
        created_at=item.created_at,
      )
      for item in recent_rows
    ]

    # TODO: compute conversion_rate from promo validation logs after analytics storage is added.
    return PromoCodeStatistics(
      promo_code_id=str(promo.id),
      code=promo.code,
      total_usages=total_usages,
      total_discount_amount=Decimal(str(total_discount)),
      total_order_amount=total_order_amount,
      unique_users=unique_users,
      usage_by_period=usage_by_period,
      recent_usages=recent_usages,
      conversion_rate=0.0,
    )

  async def overview_statistics(
    self, actor: CurrentUser, from_date: date | None, to_date: date | None
  ) -> OverviewStatistics:
    self._assert_admin_role(actor)
    payment_totals = await self.payment_repo.overview_totals(from_date, to_date)
    payment_methods = await self.payment_repo.overview_by_payment_method(from_date, to_date)
    usage_totals = await self.usage_repo.overview_totals(from_date, to_date)

    active_promos = await self.promo_repo.count_active()
    total_promos = await self.promo_repo.count_total()

    return OverviewStatistics(
      period=OverviewPeriod(from_date=from_date, to_date=to_date),
      payments=payment_totals,
      promo_codes=PromoCodesOverviewStatistics(
        active_count=active_promos,
        inactive_count=max(total_promos - active_promos, 0),
        total_usages=usage_totals.total_usages,
        total_discount_amount=usage_totals.total_discount_amount,
      ),
      payment_methods=payment_methods,
    )

  async def _to_response(self, promo: PromoCode) -> PromoCodeResponse:
    current_usages = await self.usage_repo.count_total(promo.id)
    return PromoCodeResponse(
      id=str(promo.id),
      code=promo.code,
      discount_type=promo.discount_type,
      discount_value=promo.discount_value,
      min_order_amount=promo.min_order_amount,
      valid_until=promo.valid_until,
      is_active=promo.is_active,
      max_usages_per_user=promo.max_usages_per_user,
      total_max_usages=promo.total_max_usages,
      current_usages=current_usages,
      rules_json=promo.rules_json,
      created_at=promo.created_at,
      updated_at=promo.updated_at,
      created_by=None,
    )
