import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base
from app.common.enums import BankTransferType


class BankTransferPayment(Base):
    __tablename__ = "bank_transfer_payments"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id"), nullable=True, unique=True, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id"), nullable=False
    )
    payment_type: Mapped[BankTransferType] = mapped_column(
        Enum(BankTransferType), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    vat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    iban_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    iban_bank: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban_branch: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    iban_masked: Mapped[str | None] = mapped_column(String(30), nullable=True)
    value_date: Mapped[date] = mapped_column(Date, nullable=False)
    bank_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
