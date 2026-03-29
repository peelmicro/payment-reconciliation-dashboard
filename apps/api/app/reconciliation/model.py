import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base
from app.common.enums import ReconciliationStatus


class Reconciliation(Base):
    __tablename__ = "reconciliations"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus), nullable=False
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id"), nullable=True
    )
    internal_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    stripe_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stripe_payments.id"), nullable=True
    )
    paypal_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("paypal_payments.id"), nullable=True
    )
    bank_transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bank_transfer_payments.id"), nullable=True
    )
    external_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reconciled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reconciled_by: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
