from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class PalletStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"


class ReservationStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Fund(Base):
    """Благодійний фонд — власник резервувань."""

    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default=Role.USER.value)
    is_active: Mapped[bool] = mapped_column(default=True)
    fund_id: Mapped[int | None] = mapped_column(ForeignKey("funds.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    fund: Mapped[Fund | None] = relationship()


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(120))


class Pallet(Base):
    __tablename__ = "pallets"
    __table_args__ = (CheckConstraint("units > 0", name="ck_pallet_units_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    description: Mapped[str] = mapped_column(String(200))
    units: Mapped[int]
    status: Mapped[str] = mapped_column(
        String(16), default=PalletStatus.AVAILABLE.value, index=True
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # Друга лінія захисту від подвійного бронювання: на одну палету
        # не може існувати більше одного активного резервування.
        Index(
            "uq_reservation_active_pallet",
            "pallet_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pallet_id: Mapped[int] = mapped_column(ForeignKey("pallets.id"), index=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default=ReservationStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
