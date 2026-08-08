from collections import defaultdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.database.database import get_db
from app.dependencies import require_admin
from app.models import Booking, Room, User
from app.schemas.api import BookingResponse, DashboardResponse, OccupancyResponse, RevenueResponse
from app.services import ACTIVE_BOOKING_STATUSES, booking_to_wire, money


router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


def _bookings(db: Session) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking).options(
                selectinload(Booking.user),
                selectinload(Booking.room).selectinload(Room.room_type),
            )
        ).all()
    )


def _occupancy(db: Session, bookings: list[Booking]) -> dict[str, object]:
    today = date.today()
    occupied_ids = {
        booking.room_id
        for booking in bookings
        if booking.status == "CHECKED_IN" and booking.check_in <= today < booking.check_out
    }
    rooms = list(db.scalars(select(Room)).all())
    maintenance = sum(room.status in {"MAINTENANCE", "OUT_OF_SERVICE"} for room in rooms)
    bookable = len(rooms) - maintenance
    return {
        "occupied": len(occupied_ids),
        "available": max(bookable - len(occupied_ids), 0),
        "maintenance": maintenance,
        "total_rooms": len(rooms),
        "occupancy_rate": len(occupied_ids) / bookable if bookable else 0,
    }


def _revenue(bookings: list[Booking]) -> dict[str, object]:
    today = date.today()
    current_month = today.strftime("%Y-%m")
    previous_month_day = today.replace(day=1)
    previous_month_day = (previous_month_day.fromordinal(previous_month_day.toordinal() - 1))
    previous_month = previous_month_day.strftime("%Y-%m")
    settled = [booking for booking in bookings if booking.status != "CANCELLED"]
    by_month: dict[str, float] = defaultdict(float)
    for booking in settled:
        by_month[booking.check_in.strftime("%Y-%m")] += booking.total_price
    series = [
        {"month": month, "revenue": money(value)}
        for month, value in sorted(by_month.items())[-6:]
    ]
    total_nights = sum(booking.nights for booking in settled)
    return {
        "currency": settings.currency,
        "monthly_revenue": money(by_month[current_month]),
        "previous_month_revenue": money(by_month[previous_month]),
        "average_daily_rate": money(sum(booking.subtotal for booking in settled) / total_nights) if total_nights else 0,
        "by_month": series,
    }


@router.get("/dashboard", response_model=DashboardResponse)
@cache(expire=300, namespace="reports")
def dashboard(db: Db, _admin: Admin):
    bookings = _bookings(db)
    today = date.today()
    recent = sorted(bookings, key=lambda booking: booking.created_at, reverse=True)[:5]
    return {
        "occupancy": _occupancy(db, bookings),
        "revenue": _revenue(bookings),
        "total_users": db.scalar(select(func.count()).select_from(User)) or 0,
        "active_bookings": sum(booking.status in ACTIVE_BOOKING_STATUSES for booking in bookings),
        "arrivals_today": sum(booking.check_in == today and booking.status != "CANCELLED" for booking in bookings),
        "departures_today": sum(booking.check_out == today and booking.status != "CANCELLED" for booking in bookings),
        "recent_bookings": [booking_to_wire(booking) for booking in recent],
    }


@router.get("/occupancy", response_model=OccupancyResponse)
@cache(expire=300, namespace="reports")
def occupancy(db: Db, _admin: Admin):
    bookings = _bookings(db)
    return _occupancy(db, bookings)


@router.get("/revenue", response_model=RevenueResponse)
@cache(expire=300, namespace="reports")
def revenue(db: Db, _admin: Admin):
    return _revenue(_bookings(db))


@router.get("/bookings", response_model=list[BookingResponse])
@cache(expire=300, namespace="reports")
def booking_report(db: Db, _admin: Admin):
    return [booking_to_wire(booking) for booking in _bookings(db)]