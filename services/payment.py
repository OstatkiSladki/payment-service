from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from dependency import CurrentUser
from models.payment import Payment, PaymentStatus
from models.promo_code_usage import PromoCodeUsage
from repositories.payment import PaymentRepository
from repositories.promo_code import PromoCodeRepository
from repositories.promo_code_usage import PromoCodeUsageRepository
from schemas.auth import UsersRole
from schemas.payment import PaymentCreateRequest, PaymentResponse, PaymentStatus as PaymentStatusSchema
from services.errors import ServiceError
from services.promo import PromoService


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.promo_repo = PromoCodeRepository(session)
        self.usage_repo = PromoCodeUsageRepository(session)
        self.promo_service = PromoService(session)

    async def create_payment(self, payload: PaymentCreateRequest, actor: CurrentUser) -> tuple[PaymentResponse, int]:
        if not actor.is_active:
            raise ServiceError(403, 'FORBIDDEN', 'User is inactive', actor.request_id)
        if actor.role not in {UsersRole.USER, UsersRole.STAFF, UsersRole.ADMIN}:
            raise ServiceError(403, 'FORBIDDEN', 'Role cannot create payments', actor.request_id)

        existing = await self.payment_repo.get_by_transaction_id(payload.transaction_id)
        if existing is not None:
            return self._to_response(existing), 200

        discount_amount = Decimal('0.00')
        promo_code_id: int | None = None
        promo_code_applied: str | None = None

        if payload.promo_code:
            promo_result = await self.promo_service.validate_for_payment(
                code=payload.promo_code,
                order_amount=payload.amount,
                user_id=actor.user_id,
                request_id=actor.request_id,
            )
            discount_amount = promo_result.discount_amount
            promo_code = await self.promo_repo.get_by_code(payload.promo_code)
            promo_code_id = promo_code.id if promo_code else None
            promo_code_applied = payload.promo_code

        payment = Payment(
            order_id=payload.order_id,
            user_id=actor.user_id,
            transaction_id=payload.transaction_id,
            payment_gateway='internal',
            amount=payload.amount,
            refunded_amount=Decimal('0.00'),
            currency=payload.currency,
            status=PaymentStatus.PENDING,
            payment_method=payload.payment_method.value,
            gateway_response=payload.meta,
            promo_code_id=promo_code_id,
            discount_amount=discount_amount,
        )
        await self.payment_repo.add(payment)

        if promo_code_id is not None and discount_amount > Decimal('0.00'):
            usage = PromoCodeUsage(
                promo_code_id=promo_code_id,
                user_id=actor.user_id,
                order_id=payment.order_id,
                payment_id=payment.id,
                discount_applied=discount_amount,
            )
            await self.usage_repo.add_usage(usage)

        await self.session.commit()
        await self.session.refresh(payment)

        # TODO: add OrderService validation (order ownership/status) before payment creation.
        # TODO: publish payment-created/payment-succeeded events to RabbitMQ after gateway integration.

        response = self._to_response(payment)
        response.promo_code_applied = promo_code_applied
        return response, 201

    async def list_payments(
        self,
        actor: CurrentUser,
        limit: int,
        offset: int,
        status: PaymentStatusSchema | None,
        order_id: int | None,
    ) -> tuple[list[PaymentResponse], int]:
        rows, total = await self.payment_repo.list_for_user(
            user_id=actor.user_id,
            role=actor.role,
            limit=limit,
            offset=offset,
            status=PaymentStatus(status.value) if status else None,
            order_id=order_id,
        )
        return [self._to_response(item) for item in rows], total

    async def get_payment(self, payment_id: int, actor: CurrentUser) -> PaymentResponse:
        payment = await self.payment_repo.get_for_actor(payment_id=payment_id, actor_user_id=actor.user_id, role=actor.role)
        if payment is None:
            raise ServiceError(404, 'NOT_FOUND', 'Payment not found', actor.request_id)
        return self._to_response(payment)

    async def refund_payment(self, payment_id: int, actor: CurrentUser) -> PaymentResponse:
        if actor.role != UsersRole.ADMIN:
            raise ServiceError(403, 'FORBIDDEN', 'Role cannot refund payments', actor.request_id)

        payment = await self.payment_repo.get_by_id(payment_id)
        if payment is None:
            raise ServiceError(404, 'NOT_FOUND', 'Payment not found', actor.request_id)
        if payment.status != PaymentStatus.SUCCEEDED:
            raise ServiceError(400, 'INVALID_STATE', 'Only succeeded payments can be refunded', actor.request_id)
        if payment.refunded_amount >= payment.amount:
            raise ServiceError(400, 'ALREADY_REFUNDED', 'Payment already refunded', actor.request_id)

        payment.status = PaymentStatus.REFUNDED
        payment.refunded_amount = payment.amount
        payment.refunded_at = datetime.now(timezone.utc)

        await self.payment_repo.save(payment)
        await self.session.commit()
        await self.session.refresh(payment)

        # TODO: call payment gateway refund API and map external statuses.
        return self._to_response(payment)

    @staticmethod
    def _to_response(payment: Payment) -> PaymentResponse:
        method_value = payment.payment_method if isinstance(payment.payment_method, str) else getattr(payment.payment_method, 'value', None)
        return PaymentResponse(
            id=str(payment.id),
            order_id=payment.order_id,
            transaction_id=payment.transaction_id,
            amount=payment.amount,
            refunded_amount=payment.refunded_amount,
            currency=payment.currency,
            status=PaymentStatusSchema(payment.status.value),
            payment_method=method_value,
            promo_code_applied=None,
            discount_amount=payment.discount_amount,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
            paid_at=payment.paid_at,
            refunded_at=payment.refunded_at,
        )
