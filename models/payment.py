from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BIGINT, DECIMAL, JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PaymentMethod(StrEnum):
    BANK_CARD = 'bank_card'
    SBP = 'sbp'


class PaymentStatus(StrEnum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'


class Payment(Base):
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BIGINT, index=True)
    user_id: Mapped[int] = mapped_column(BIGINT, index=True)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    payment_gateway: Mapped[str] = mapped_column(String(50), default='internal')
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    refunded_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=Decimal('0.00'))
    currency: Mapped[str] = mapped_column(String(3), default='RUB')
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name='payment_status', schema='public'),
        default=PaymentStatus.PENDING,
        index=True,
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name='payment_method', schema='public'),
        nullable=True,
    )
    gateway_response: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    promo_code_id: Mapped[int | None] = mapped_column(
        ForeignKey('public.promo_codes.id', ondelete='SET NULL'),
        nullable=True,
    )
    discount_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=Decimal('0.00'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
