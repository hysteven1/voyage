import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))

    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    travelers: Mapped[int] = mapped_column(Integer)

    budget: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    preferences: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
