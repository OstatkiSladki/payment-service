from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.promo_code_usage import PromoCodeUsage
from repositories.base import BaseRepository
from schemas.queries import StatsPeriod


class PromoCodeUsageRepository(BaseRepository[PromoCodeUsage]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PromoCodeUsage)

    async def count_for_user(self, promo_code_id: int, user_id: int) -> int:
        total = await self.session.scalar(
            select(func.count(PromoCodeUsage.id)).where(
                PromoCodeUsage.promo_code_id == promo_code_id,
                PromoCodeUsage.user_id == user_id,
            )
        )
        return int(total or 0)

    async def count_total(self, promo_code_id: int) -> int:
        total = await self.session.scalar(select(func.count(PromoCodeUsage.id)).where(PromoCodeUsage.promo_code_id == promo_code_id))
        return int(total or 0)

    async def sum_discount(self, promo_code_id: int) -> float:
        value = await self.session.scalar(
            select(func.coalesce(func.sum(PromoCodeUsage.discount_applied), 0)).where(PromoCodeUsage.promo_code_id == promo_code_id)
        )
        return float(value or 0)

    async def count_unique_users(self, promo_code_id: int) -> int:
        value = await self.session.scalar(
            select(func.count(func.distinct(PromoCodeUsage.user_id))).where(PromoCodeUsage.promo_code_id == promo_code_id)
        )
        return int(value or 0)

    async def recent_entries(self, promo_code_id: int, limit: int = 10) -> Sequence[PromoCodeUsage]:
        rows = await self.session.execute(
            select(PromoCodeUsage)
            .where(PromoCodeUsage.promo_code_id == promo_code_id)
            .order_by(PromoCodeUsage.created_at.desc())
            .limit(limit)
        )
        return rows.scalars().all()

    async def usage_by_period(
        self,
        promo_code_id: int,
        period: StatsPeriod,
    ) -> list[dict[str, str | int | float | datetime]]:
        if period == StatsPeriod.ALL:
            count = await self.count_total(promo_code_id)
            amount = await self.sum_discount(promo_code_id)
            return [{'period': StatsPeriod.ALL.value, 'usages': count, 'discount_amount': amount}]

        bucket = {
            StatsPeriod.DAY: 'day',
            StatsPeriod.WEEK: 'week',
            StatsPeriod.MONTH: 'month',
        }[period]
        rows = await self.session.execute(
            select(
                func.date_trunc(bucket, PromoCodeUsage.created_at).label('period'),
                func.count(PromoCodeUsage.id).label('usages'),
                func.coalesce(func.sum(PromoCodeUsage.discount_applied), 0).label('discount_amount'),
            )
            .where(PromoCodeUsage.promo_code_id == promo_code_id)
            .group_by(func.date_trunc(bucket, PromoCodeUsage.created_at))
            .order_by(func.date_trunc(bucket, PromoCodeUsage.created_at))
        )
        return [
            {
                'period': item.period,
                'usages': int(item.usages),
                'discount_amount': float(item.discount_amount),
            }
            for item in rows
        ]

    async def add_usage(self, usage: PromoCodeUsage) -> PromoCodeUsage:
        self.session.add(usage)
        await self.session.flush()
        return usage
