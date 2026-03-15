from datetime import datetime
from decimal import Decimal

from sqlalchemy import BIGINT, BOOLEAN, DECIMAL, JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PromoCode(Base):
    __tablename__ = 'promo_codes'
    __table_args__ = {'schema': 'public'}

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    discount_type: Mapped[str] = mapped_column(String(20))
    discount_value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
    min_order_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=Decimal('0.00'))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(BOOLEAN, default=True)
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict)
    max_usages_per_user: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_max_usages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue_id: Mapped[int | None] = mapped_column(BIGINT, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
