from datetime import date
from typing import Annotated
import logging
from app.notifications import send_booking_confirmation_email

from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import problem
from app.database.database import get_db
from app.dependencies import get_current_user, get_redis
from app.models import Booking, Room, User, utc_now
from app.schemas.api import BookingCreateRequest, BookingResponse, BookingUpdateRequest
from app.services import (
    ACTIVE_BOOKING_STATUSES,
    booking_to_wire,
    money,
    price_stay,
    room_is_free,
    validate_stay_dates,
)


router = APIRouter()
logger = logging.getLogger(__name__)
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
RedisClient = Annotated[Redis, Depends(get_redis)]


def _booking_query():
    return select(Booking).options(
        selectinload(Booking.user),
        selectinload(Booking.room).selectinload(Room.room_type),
    )


def _visible_booking(db: Session, booking_id: int, current_user: User) -> Booking:
    booking = db.scalar(_booking_query().where(Booking.id == booking_id))
    if not booking or (current_user.role != "ADMIN" and booking.user_id != current_user.id):
        problem(404, "We could not find that booking.")
    return booking


@router.get("/", response_model=list[BookingResponse])
def list_bookings(
    current_user: CurrentUser,
    db: Db,
    booking_status: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
):
    query = _booking_query()
    if current_user.role != "ADMIN":
        query = query.where(Booking.user_id == current_user.id)
    if booking_status and booking_status != "ALL":
        query = query.where(Booking.status == booking_status)
    if from_date:
        query = query.where(Booking.check_out >= from_date)
    if to_date:
        query = query.where(Booking.check_in <= to_date)
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.join(Booking.user).join(Booking.room).where(
            or_(
                func.lower(Booking.reference).like(term),
                func.lower(User.full_name).like(term),
                func.lower(Room.room_number).like(term),
            )
        )
    bookings = db.scalars(query.order_by(Booking.check_in.desc())).unique().all()
    return [booking_to_wire(booking) for booking in bookings]


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, current_user: CurrentUser, db: Db):
    return booking_to_wire(_visible_booking(db, booking_id, current_user))


@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    payload: BookingCreateRequest,
    current_user: CurrentUser,
    db: Db,
    redis: RedisClient,
):
    nights = validate_stay_dates(
        payload.check_in,
        payload.check_out,
    )

    # Redis distributed lock prevents two users/workers
    # from booking the same room simultaneously.
    async with redis.lock(
        f"lock:room:{payload.room_id}",
        timeout=5,
    ):
        room = db.scalar(
            select(Room)
            .options(selectinload(Room.room_type))
            .where(Room.id == payload.room_id)
        )

        if not room:
            problem(
                404,
                "We could not find that room.",
            )

        if payload.guests > room.room_type.max_occupancy:
            problem(
                400,
                f"This room sleeps a maximum of "
                f"{room.room_type.max_occupancy} guests.",
                {
                    "guests": (
                        f"Maximum "
                        f"{room.room_type.max_occupancy} "
                        f"guests for this room."
                    )
                },
            )

        if room.status in {
            "MAINTENANCE",
            "OUT_OF_SERVICE",
        }:
            problem(
                409,
                "This room is not currently bookable.",
            )

        if not room_is_free(
            db,
            room.id,
            payload.check_in,
            payload.check_out,
        ):
            problem(
                409,
                "Sorry — that room was just booked "
                "for those dates. Please choose another.",
            )

        price = price_stay(
            room,
            nights,
        )

        booking = Booking(
            reference="pending",
            user_id=current_user.id,
            room_id=room.id,
            check_in=payload.check_in,
            check_out=payload.check_out,
            guests=payload.guests,
            nights=nights,
            nightly_rate=room.nightly_rate,
            subtotal=price["subtotal"],
            taxes=price["taxes"],
            total_price=price["total"],
            currency=settings.currency,
            status="CONFIRMED",
            special_requests=(
                payload.special_requests or None
            ),
        )

        db.add(booking)

        # Flush assigns the database-generated ID.
        db.flush()

        booking.reference = (
            f"AG-{booking.id:05d}"
        )

        db.commit()

        # Refresh relationships after commit so the
        # notification service has the latest data.
        db.refresh(booking)

    # Send the email AFTER the booking has been committed.
    #
    # Email failure must NOT make the booking fail.
    try:
        send_booking_confirmation_email(booking)
    except Exception:
        logger.exception(
            "Failed to send booking confirmation email "
            "for booking %s to %s",
            booking.reference,
            current_user.email,
        )

    return booking_to_wire(
        _visible_booking(
            db,
            booking.id,
            current_user,
        )
    )


@router.patch("/{booking_id}", response_model=BookingResponse)
@router.put("/{booking_id}", response_model=BookingResponse, include_in_schema=False)
def update_booking(booking_id: int, payload: BookingUpdateRequest, current_user: CurrentUser, db: Db):
    booking = _visible_booking(db, booking_id, current_user)
    if booking.status in {"CANCELLED", "CHECKED_OUT"} and current_user.role != "ADMIN":
        problem(409, "A closed booking cannot be changed.")
    if payload.status is not None and current_user.role != "ADMIN":
        problem(403, "Only staff can change a booking status.")
    if booking.status == "CANCELLED" and payload.status not in {None, "CANCELLED"}:
        problem(409, "A cancelled booking cannot be reinstated. Please book again.")

    check_in = payload.check_in or booking.check_in
    check_out = payload.check_out or booking.check_out
    guests = payload.guests or booking.guests
    dates_changed = check_in != booking.check_in or check_out != booking.check_out
    nights = booking.nights
    
    if dates_changed:
        nights = validate_stay_dates(check_in, check_out)
        if not room_is_free(db, booking.room_id, check_in, check_out, booking.id):
            problem(409, "That room is already booked for the new dates.")
    if guests > booking.room.room_type.max_occupancy:
        problem(400, f"This room sleeps a maximum of {booking.room.room_type.max_occupancy} guests.", {"guests": f"Maximum {booking.room.room_type.max_occupancy} guests for this room."})

    price = price_stay(booking.room, nights)
    booking.check_in = check_in
    booking.check_out = check_out
    booking.guests = guests
    booking.nights = nights
    booking.subtotal = price["subtotal"]
    booking.taxes = price["taxes"]
    booking.total_price = price["total"]
    if payload.status is not None:
        booking.status = payload.status
    if "special_requests" in payload.model_fields_set:
        booking.special_requests = payload.special_requests or None
    booking.updated_at = utc_now()
    db.commit()
    return booking_to_wire(_visible_booking(db, booking_id, current_user))


@router.delete("/{booking_id}", response_model=BookingResponse)
def cancel_booking(booking_id: int, current_user: CurrentUser, db: Db):
    booking = _visible_booking(db, booking_id, current_user)
    if booking.status == "CANCELLED":
        problem(409, "This booking has already been cancelled.")
    if booking.status == "CHECKED_OUT":
        problem(409, "A completed stay cannot be cancelled.")
    booking.status = "CANCELLED"
    booking.updated_at = utc_now()
    db.commit()
    return booking_to_wire(_visible_booking(db, booking_id, current_user))