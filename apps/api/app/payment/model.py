import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base
from app.common.enums import PaymentMethod, PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fee: Mapped[int] = mapped_column(Integer, nullable=False)
    net: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    # Card fields (used when payment_method is card)
    card_bin: Mapped[str | None] = mapped_column(String(6), nullable=True)
    card_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_masked: Mapped[str | None] = mapped_column(String(19), nullable=True)
    # IBAN fields (used when payment_method is bank_transfer or direct_debit)
    iban_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    iban_bank: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban_branch: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban_masked: Mapped[str | None] = mapped_column(String(30), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
