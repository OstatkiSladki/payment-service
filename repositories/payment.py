from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import Payment, PaymentStatus
from repositories.base import BaseRepository
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
