from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="REGISTERED_USER")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    biometric_credentials: Mapped[list["BiometricCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RoomType(Base):
    __tablename__ = "app_room_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    max_occupancy: Mapped[int] = mapped_column(Integer)
    base_rate: Mapped[float] = mapped_column(Float)
    amenities_json: Mapped[str] = mapped_column(Text, default="[]")
    image_url: Mapped[str] = mapped_column(Text, default="")

    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")


class Room(Base):
    __tablename__ = "app_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    floor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="AVAILABLE")
    room_type_id: Mapped[int] = mapped_column(ForeignKey("app_room_types.id"))
    nightly_rate: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, default="")

    room_type: Mapped[RoomType] = relationship(back_populates="rooms")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room")


class Booking(Base):
    __tablename__ = "app_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("app_rooms.id"), index=True)
    check_in: Mapped[date] = mapped_column(Date, index=True)
    check_out: Mapped[date] = mapped_column(Date, index=True)
    guests: Mapped[int] = mapped_column(Integer)
    nights: Mapped[int] = mapped_column(Integer)
    nightly_rate: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)
    taxes: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    status: Mapped[str] = mapped_column(String(24), default="CONFIRMED", index=True)
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship(back_populates="bookings")
    room: Mapped[Room] = relationship(back_populates="bookings")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )


class Payment(Base):
    __tablename__ = "app_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("app_bookings.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    method: Mapped[str] = mapped_column(String(24))
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    booking: Mapped[Booking] = relationship(back_populates="payments")


class RefreshSession(Base):
    __tablename__ = "app_refresh_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_sessions")


class BiometricCredential(Base):
    """A biometric enrolment bound to one device for one user.

    The device holds the plaintext secret behind the OS keystore; we only ever
    store its PBKDF2 hash, so a database leak cannot be replayed as a login.
    Revoking a row (from the admin web UI or the owner's profile page) is what
    makes a remote biometric reset take effect on the phone.
    """

    __tablename__ = "app_biometric_credentials"
    __table_args__ = (UniqueConstraint("user_id", "device_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    device_label: Mapped[str] = mapped_column(String(80), default="")
    secret_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="biometric_credentials")


class Guest(Base):
    __tablename__ = "app_guests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)


__all__ = [
    "BiometricCredential",
    "Booking",
    "Guest",
    "Payment",
    "RefreshSession",
    "Room",
    "RoomType",
    "User",
]
