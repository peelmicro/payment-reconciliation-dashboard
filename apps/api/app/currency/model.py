from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    iso_number: Mapped[str] = mapped_column(String(3), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False)
    decimal_points: Mapped[int] = mapped_column(Integer, nullable=False)
