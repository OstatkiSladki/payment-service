from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.promo_code import PromoCode
from repositories.base import BaseRepository


class PromoCodeRepository(BaseRepository[PromoCode]):
  def __init__(self, session: AsyncSession):
    super().__init__(session, PromoCode)

  async def get_by_code(self, code: str) -> PromoCode | None:
    result = await self.session.execute(select(PromoCode).where(PromoCode.code == code))
    return result.scalar_one_or_none()

  async def list_for_admin(
    self,
    limit: int,
    offset: int,
    is_active: bool | None = None,
    discount_type: str | None = None,
    search: str | None = None,
  ) -> tuple[Sequence[PromoCode], int]:
    clauses = []
    if is_active is not None:
      clauses.append(PromoCode.is_active == is_active)
    if discount_type is not None:
      clauses.append(PromoCode.discount_type == discount_type)
    if search:
      clauses.append(PromoCode.code.ilike(f"%{search}%"))

    query = select(PromoCode).order_by(PromoCode.created_at.desc()).limit(limit).offset(offset)
    count_query = select(func.count(PromoCode.id))

    if clauses:
      query = query.where(and_(*clauses))
      count_query = count_query.where(and_(*clauses))

    rows = await self.session.execute(query)
    total = await self.session.scalar(count_query)
    return rows.scalars().all(), int(total or 0)

  async def get_for_admin(self, promo_id: int) -> PromoCode | None:
    result = await self.session.execute(select(PromoCode).where(PromoCode.id == promo_id))
    return result.scalar_one_or_none()

  async def count_total(self) -> int:
    total = await self.session.scalar(select(func.count(PromoCode.id)))
    return int(total or 0)

  async def count_active(self) -> int:
    total = await self.session.scalar(
      select(func.count(PromoCode.id)).where(PromoCode.is_active.is_(True))
    )
    return int(total or 0)

  async def save(self, promo: PromoCode) -> PromoCode:
    self.session.add(promo)
    await self.session.flush()
    return promo
