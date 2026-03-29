import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base
from app.common.enums import StripePaymentType


class StripePayment(Base):
    __tablename__ = "stripe_payments"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id"), nullable=True, unique=True, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id"), nullable=False
    )
    payment_intent_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    charge_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_type: Mapped[StripePaymentType] = mapped_column(
        Enum(StripePaymentType), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fee: Mapped[int] = mapped_column(Integer, nullable=False)
    net: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    refunded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    card_bin: Mapped[str | None] = mapped_column(String(6), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_masked: Mapped[str | None] = mapped_column(String(19), nullable=True)
    card_brand: Mapped[str | None] = mapped_column(String(20), nullable=True)
    card_funding: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stripe_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
