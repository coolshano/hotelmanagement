from __future__ import annotations

import json
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import problem
from app.models import BiometricCredential, Booking, Payment, Room, RoomType, User


ACTIVE_BOOKING_STATUSES = ("PENDING", "CONFIRMED", "CHECKED_IN")
FALLBACK_IMAGE = (
    "https://images.unsplash.com/photo-1566665797739-1674de7a421a?"
    "auto=format&fit=crop&w=1200&q=70"
)


def money(value: float) -> float:
    return round(value + 1e-10, 2)


def validate_stay_dates(check_in: date, check_out: date) -> int:
    nights = (check_out - check_in).days
    if nights <= 0:
        problem(
            400,
            "The check-out date must be after the check-in date.",
            {"check_out": "Check-out must be after check-in."},
        )
    if check_in < date.today():
        problem(
            400,
            "The check-in date cannot be in the past.",
            {"check_in": "Choose today or a later date."},
        )
    if nights > 30:
        problem(
            400,
            "Stays longer than 30 nights must be arranged with the front desk.",
            {"check_out": "Maximum stay is 30 nights."},
        )
    return nights


def room_is_free(
    db: Session,
    room_id: int,
    check_in: date,
    check_out: date,
    ignore_booking_id: int | None = None,
) -> bool:
    conditions = [
        Booking.room_id == room_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    ]
    if ignore_booking_id is not None:
        conditions.append(Booking.id != ignore_booking_id)
    return db.scalar(select(Booking.id).where(and_(*conditions)).limit(1)) is None


def price_stay(room: Room, nights: int) -> dict[str, float]:
    subtotal = money(room.nightly_rate * nights)
    taxes = money(subtotal * settings.tax_rate)
    return {"subtotal": subtotal, "taxes": taxes, "total": money(subtotal + taxes)}


def user_to_wire(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at,
    }


def biometric_to_wire(credential: BiometricCredential) -> dict[str, object]:
    return {
        "id": credential.id,
        "device_id": credential.device_id,
        "device_label": credential.device_label,
        "created_at": credential.created_at,
        "last_used_at": credential.last_used_at,
    }


def room_type_to_wire(room_type: RoomType) -> dict[str, object]:
    try:
        amenities = json.loads(room_type.amenities_json)
    except (TypeError, json.JSONDecodeError):
        amenities = []
    return {
        "id": room_type.id,
        "name": room_type.name,
        "description": room_type.description,
        "max_occupancy": room_type.max_occupancy,
        "base_rate": room_type.base_rate,
        "amenities": amenities,
        "image_url": room_type.image_url or FALLBACK_IMAGE,
    }


def room_to_wire(room: Room) -> dict[str, object]:
    return {
        "id": room.id,
        "room_number": room.room_number,
        "floor": room.floor,
        "status": room.status,
        "room_type_id": room.room_type_id,
        "room_type": room_type_to_wire(room.room_type),
        "nightly_rate": room.nightly_rate,
        "description": room.description or room.room_type.description,
    }


def availability_to_wire(room: Room, nights: int) -> dict[str, object]:
    price = price_stay(room, nights)
    return {
        "room": room_to_wire(room),
        "nights": nights,
        "nightly_rate": room.nightly_rate,
        **price,
        "currency": settings.currency,
    }


def booking_to_wire(booking: Booking) -> dict[str, object]:
    return {
        "id": booking.id,
        "reference": booking.reference,
        "user_id": booking.user_id,
        "guest_name": booking.user.full_name,
        "guest_email": booking.user.email,
        "room_id": booking.room_id,
        "room": room_to_wire(booking.room),
        "check_in": booking.check_in,
        "check_out": booking.check_out,
        "guests": booking.guests,
        "nights": booking.nights,
        "nightly_rate": booking.nightly_rate,
        "subtotal": booking.subtotal,
        "taxes": booking.taxes,
        "total_price": booking.total_price,
        "currency": booking.currency,
        "status": booking.status,
        "special_requests": booking.special_requests,
        "created_at": booking.created_at,
        "updated_at": booking.updated_at,
    }


def payment_to_wire(payment: Payment) -> dict[str, object]:
    return {
        "id": payment.id,
        "booking_id": payment.booking_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "method": payment.method,
        "paid_at": payment.paid_at,
    }

