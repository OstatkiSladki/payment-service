from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import Payment, PaymentStatus
from repositories.base import BaseRepository
from schemas.admin import PaymentMethodStatistics, PaymentOverviewStatistics
from schemas.auth import UsersRole


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Payment)

    async def get_by_transaction_id(self, transaction_id: str) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.transaction_id == transaction_id))
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        role: UsersRole,
        limit: int,
        offset: int,
        status: PaymentStatus | None = None,
        order_id: int | None = None,
    ) -> tuple[Sequence[Payment], int]:
        clauses = []
        if role != UsersRole.ADMIN:
            clauses.append(Payment.user_id == user_id)
        if status is not None:
            clauses.append(Payment.status == status)
        if order_id is not None:
            clauses.append(Payment.order_id == order_id)

        query = select(Payment).order_by(Payment.created_at.desc()).limit(limit).offset(offset)
        count_query = select(func.count(Payment.id))

        if clauses:
            query = query.where(and_(*clauses))
            count_query = count_query.where(and_(*clauses))

        rows = await self.session.execute(query)
        total = await self.session.scalar(count_query)
        return rows.scalars().all(), int(total or 0)

    async def get_by_id(self, payment_id: int) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_for_actor(self, payment_id: int, actor_user_id: int, role: UsersRole) -> Payment | None:
        query = select(Payment).where(Payment.id == payment_id)
        if role != UsersRole.ADMIN:
            query = query.where(Payment.user_id == actor_user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def save(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    @staticmethod
    def _apply_created_date_filter(query, from_date: date | None, to_date: date | None):
        if from_date is not None:
            query = query.where(func.date(Payment.created_at) >= from_date)
        if to_date is not None:
            query = query.where(func.date(Payment.created_at) <= to_date)
        return query

    async def sum_amount_for_promo(self, promo_id: int) -> Decimal:
        value = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.promo_code_id == promo_id)
        )
        return Decimal(str(value or 0))

    async def overview_totals(self, from_date: date | None, to_date: date | None) -> PaymentOverviewStatistics:
        query = select(
            func.count(Payment.id).label('total_count'),
            func.coalesce(
                func.sum(case((Payment.status == PaymentStatus.SUCCEEDED, 1), else_=0)),
                0,
            ).label('succeeded_count'),
            func.coalesce(
                func.sum(case((Payment.status == PaymentStatus.FAILED, 1), else_=0)),
                0,
            ).label('failed_count'),
            func.coalesce(
                func.sum(case((Payment.status == PaymentStatus.REFUNDED, 1), else_=0)),
                0,
            ).label('refunded_count'),
            func.coalesce(func.sum(Payment.amount), 0).label('total_amount'),
            func.coalesce(func.sum(Payment.refunded_amount), 0).label('total_refunded_amount'),
        )
        query = self._apply_created_date_filter(query, from_date, to_date)
        row = (await self.session.execute(query)).one()
        return PaymentOverviewStatistics(
            total_count=int(row.total_count or 0),
            succeeded_count=int(row.succeeded_count or 0),
            failed_count=int(row.failed_count or 0),
            refunded_count=int(row.refunded_count or 0),
            total_amount=Decimal(str(row.total_amount or 0)),
            total_refunded_amount=Decimal(str(row.total_refunded_amount or 0)),
        )

    async def overview_by_payment_method(
        self,
        from_date: date | None,
        to_date: date | None,
    ) -> list[PaymentMethodStatistics]:
        query = (
            select(
                Payment.payment_method.label('method'),
                func.count(Payment.id).label('count'),
                func.coalesce(func.sum(Payment.amount), 0).label('amount'),
            )
            .where(Payment.payment_method.is_not(None))
            .group_by(Payment.payment_method)
        )
        query = self._apply_created_date_filter(query, from_date, to_date)

        rows = await self.session.execute(query)
        return [
            PaymentMethodStatistics(
                method=row.method.value if hasattr(row.method, 'value') else str(row.method),
                count=int(row.count or 0),
                amount=Decimal(str(row.amount or 0)),
            )
            for row in rows
        ]
