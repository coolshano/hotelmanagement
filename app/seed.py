from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Booking, Payment, Room, RoomType, User
from app.services import money


ROOM_TYPES = [
    (1, "Classic Double", "A calm 24 m² room with a queen bed, city-facing window and a walk-in rain shower.", 2, 129, ["Queen bed", "Rain shower", "Desk", "Free Wi-Fi", "Air conditioning"], "https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1200&q=70"),
    (2, "Deluxe King", "A 34 m² king room with a seating nook, marble bathroom and garden views.", 3, 189, ["King bed", "Seating area", "Bathtub", "Nespresso machine", "Free Wi-Fi", "Air conditioning"], "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=70"),
    (3, "Family Suite", "Two connected rooms with a king bed, twin beds and a shared lounge.", 5, 259, ["King + twin beds", "Separate lounge", "Two bathrooms", "Kettle & microwave", "Free Wi-Fi"], "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=1200&q=70"),
    (4, "Executive Suite", "A corner suite with a private terrace, dining table and lounge access.", 4, 379, ["King bed", "Private terrace", "Dining area", "Lounge access", "Espresso bar", "Free Wi-Fi"], "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=70"),
    (5, "Garden Studio", "A ground-floor studio opening onto the garden, with a kitchenette and step-free access.", 2, 159, ["Queen bed", "Kitchenette", "Step-free access", "Garden patio", "Free Wi-Fi"], "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=70"),
]

USERS = [
    (1, "admin@auroragrand.test", "Priya Raman", "+44 20 7946 0011", "ADMIN", "ACTIVE", "Admin#2026"),
    (2, "ella.hart@example.test", "Ella Hart", "+44 7700 900142", "REGISTERED_USER", "ACTIVE", "Guest#2026"),
    (3, "noah.reid@example.test", "Noah Reid", "+44 7700 900318", "REGISTERED_USER", "ACTIVE", "Guest#2026"),
    (4, "maya.osei@example.test", "Maya Osei", "+44 7700 900527", "REGISTERED_USER", "ACTIVE", "Guest#2026"),
    (5, "tomas.silva@example.test", "Tomas Silva", None, "REGISTERED_USER", "SUSPENDED", "Guest#2026"),
    (6, "front.desk@auroragrand.test", "Daniel Okafor", "+44 20 7946 0019", "ADMIN", "ACTIVE", "Admin#2026"),
    (7, "test@example.com", "API Test User", None, "REGISTERED_USER", "ACTIVE", "P@ssw0rd123"),
]

ROOMS = [
    (1, "101", 1, 5, "AVAILABLE", 159),
    (2, "102", 1, 5, "AVAILABLE", 169),
    (3, "103", 1, 1, "MAINTENANCE", 129),
    (4, "201", 2, 1, "AVAILABLE", 129),
    (5, "202", 2, 1, "AVAILABLE", 129),
    (6, "203", 2, 1, "OCCUPIED", 129),
    (7, "204", 2, 2, "AVAILABLE", 189),
    (8, "205", 2, 2, "AVAILABLE", 204),
    (9, "301", 3, 2, "AVAILABLE", 189),
    (10, "302", 3, 3, "AVAILABLE", 259),
    (11, "303", 3, 3, "OCCUPIED", 259),
    (12, "401", 4, 4, "AVAILABLE", 379),
    (13, "402", 4, 4, "AVAILABLE", 419),
    (14, "403", 4, 2, "OUT_OF_SERVICE", 189),
]

BOOKINGS = [
    (1, 2, 7, 4, 3, 2, "CONFIRMED", "High floor if possible, arriving late (~23:00)."),
    (2, 2, 10, 32, 4, 4, "PENDING", None),
    (3, 2, 4, -21, 2, 1, "CHECKED_OUT", None),
    (4, 3, 6, -1, 3, 2, "CHECKED_IN", None),
    (5, 3, 12, 12, 2, 2, "CONFIRMED", "Anniversary — flowers on arrival."),
    (6, 4, 11, 0, 5, 5, "CHECKED_IN", None),
    (7, 4, 5, -40, 1, 1, "CANCELLED", None),
    (8, 5, 9, 18, 2, 2, "CONFIRMED", None),
    (9, 3, 1, -12, 3, 2, "CHECKED_OUT", None),
    (10, 4, 13, 45, 6, 3, "PENDING", None),
]


def seed_database(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(User)):
        return

    for user_id, email, name, phone, role, status, password in USERS:
        db.add(User(id=user_id, email=email, full_name=name, phone=phone, role=role, status=status, password_hash=hash_password(password), created_at=datetime(2026, 1, 12, 9, 14)))

    room_types: dict[int, RoomType] = {}
    for type_id, name, description, capacity, rate, amenities, image_url in ROOM_TYPES:
        room_type = RoomType(id=type_id, name=name, description=description, max_occupancy=capacity, base_rate=rate, amenities_json=json.dumps(amenities), image_url=image_url)
        room_types[type_id] = room_type
        db.add(room_type)

    rooms: dict[int, Room] = {}
    for room_id, number, floor, type_id, status, rate in ROOMS:
        room = Room(id=room_id, room_number=number, floor=floor, room_type_id=type_id, status=status, nightly_rate=rate, description=room_types[type_id].description)
        rooms[room_id] = room
        db.add(room)

    db.flush()
    today = date.today()
    payment_id = 1
    for booking_id, user_id, room_id, offset, nights, guests, status, requests in BOOKINGS:
        check_in = today + timedelta(days=offset)
        check_out = check_in + timedelta(days=nights)
        room = rooms[room_id]
        subtotal = money(room.nightly_rate * nights)
        taxes = money(subtotal * settings.tax_rate)
        created_at = datetime.combine(check_in - timedelta(days=min(nights + 10, 30)), time(10, 12))
        booking = Booking(
            id=booking_id,
            reference=f"AG-{booking_id:05d}",
            user_id=user_id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            nights=nights,
            nightly_rate=room.nightly_rate,
            subtotal=subtotal,
            taxes=taxes,
            total_price=money(subtotal + taxes),
            currency=settings.currency,
            status=status,
            special_requests=requests,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(booking)
        if status not in {"PENDING", "CANCELLED"}:
            methods = ("CARD", "BANK_TRANSFER", "CASH")
            db.add(Payment(id=payment_id, booking_id=booking_id, amount=booking.total_price, currency=settings.currency, method=methods[(payment_id - 1) % 3], paid_at=created_at + timedelta(hours=2)))
            payment_id += 1

    db.commit()

