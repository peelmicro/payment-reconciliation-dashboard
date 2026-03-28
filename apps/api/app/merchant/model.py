import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(300), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    currency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    vat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
