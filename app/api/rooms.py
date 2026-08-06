from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import problem
from app.database.database import get_db
from app.dependencies import require_admin
from app.models import Booking, Room, RoomType, User
from app.schemas.api import AvailabilityResponse, RoomResponse, RoomWriteRequest
from app.services import (
    ACTIVE_BOOKING_STATUSES,
    availability_to_wire,
    room_is_free,
    room_to_wire,
    validate_stay_dates,
)


router = APIRouter()
availability_router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


def _rooms_query():
    return select(Room).options(selectinload(Room.room_type))


@router.get("/", response_model=list[RoomResponse])
def list_rooms(db: Db):
    rooms = db.scalars(_rooms_query().order_by(Room.room_number)).all()
    return [room_to_wire(room) for room in rooms]


@router.get("/available", response_model=list[RoomResponse])
def available_rooms(db: Db):
    rooms = db.scalars(
        _rooms_query().where(Room.status.in_(("AVAILABLE", "OCCUPIED"))).order_by(Room.room_number)
    ).all()
    return [room_to_wire(room) for room in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, db: Db):
    room = db.scalar(_rooms_query().where(Room.id == room_id))
    if not room:
        problem(404, "We could not find that room.")
    return room_to_wire(room)


@router.get("/{room_id}/quote", response_model=AvailabilityResponse)
def quote_room(room_id: int, check_in: date, check_out: date, db: Db):
    nights = validate_stay_dates(check_in, check_out)
    room = db.scalar(_rooms_query().where(Room.id == room_id))
    if not room:
        problem(404, "We could not find that room.")
    return availability_to_wire(room, nights)


@availability_router.get("/availability", response_model=list[AvailabilityResponse])
def search_availability(
    check_in: date,
    check_out: date,
    guests: Annotated[int, Query(ge=1, le=8)],
    db: Db,
    room_type_id: int | None = None,
    max_nightly_rate: float | None = Query(default=None, gt=0),
):
    nights = validate_stay_dates(check_in, check_out)
    query = _rooms_query().where(Room.status.in_(("AVAILABLE", "OCCUPIED")))
    if room_type_id:
        query = query.where(Room.room_type_id == room_type_id)
    if max_nightly_rate:
        query = query.where(Room.nightly_rate <= max_nightly_rate)
    rooms = db.scalars(query.order_by(Room.nightly_rate)).all()
    results = [
        availability_to_wire(room, nights)
        for room in rooms
        if room.room_type.max_occupancy >= guests
        and room_is_free(db, room.id, check_in, check_out)
    ]
    return sorted(results, key=lambda result: float(result["total"]))


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomWriteRequest, db: Db, _admin: Admin):
    if db.scalar(select(Room.id).where(Room.room_number == payload.room_number)):
        problem(409, "A room with that number already exists.", {"room_number": "This room number is already in use."})
    room_type = db.get(RoomType, payload.room_type_id)
    if not room_type:
        problem(400, "Select a valid room type.", {"room_type_id": "Select a valid room type."})
    room = Room(
        room_number=payload.room_number,
        floor=payload.floor,
        status=payload.status,
        room_type_id=payload.room_type_id,
        nightly_rate=payload.nightly_rate,
        description=payload.description or room_type.description,
    )
    db.add(room)
    db.commit()
    return room_to_wire(db.scalar(_rooms_query().where(Room.id == room.id)))


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(room_id: int, payload: RoomWriteRequest, db: Db, _admin: Admin):
    room = db.get(Room, room_id)
    if not room:
        problem(404, "We could not find that room.")
    duplicate = db.scalar(select(Room.id).where(Room.room_number == payload.room_number, Room.id != room_id))
    if duplicate:
        problem(409, "A room with that number already exists.", {"room_number": "This room number is already in use."})
    room_type = db.get(RoomType, payload.room_type_id)
    if not room_type:
        problem(400, "Select a valid room type.", {"room_type_id": "Select a valid room type."})
    room.room_number = payload.room_number
    room.floor = payload.floor
    room.status = payload.status
    room.room_type_id = payload.room_type_id
    room.nightly_rate = payload.nightly_rate
    room.description = payload.description or room_type.description
    db.commit()
    return room_to_wire(db.scalar(_rooms_query().where(Room.id == room_id)))


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: Db, _admin: Admin):
    room = db.get(Room, room_id)
    if not room:
        problem(404, "We could not find that room.")
    if db.scalar(select(Booking.id).where(Booking.room_id == room_id).limit(1)):
        problem(409, "This room has booking history and cannot be deleted. Mark it out of service instead.")
    db.delete(room)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
