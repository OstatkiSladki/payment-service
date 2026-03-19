from datetime import datetime
from decimal import Decimal

from sqlalchemy import BIGINT, DECIMAL, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PromoCodeUsage(Base):
  __tablename__ = "promo_code_usages"

  id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
  promo_code_id: Mapped[int] = mapped_column(
    ForeignKey("public.promo_codes.id", ondelete="CASCADE"), index=True
  )
  user_id: Mapped[int] = mapped_column(BIGINT, index=True)
  order_id: Mapped[int | None] = mapped_column(BIGINT, index=True, nullable=True)
  payment_id: Mapped[int | None] = mapped_column(BIGINT, index=True, nullable=True)
  discount_applied: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
