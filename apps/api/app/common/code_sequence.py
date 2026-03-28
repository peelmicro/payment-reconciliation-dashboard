from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base


class CodeSequence(Base):
    __tablename__ = "code_sequences"

    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("prefix", "year_month", name="uq_prefix_year_month"),
    )
