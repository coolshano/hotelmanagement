import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.database.database import get_db
from app.dependencies import require_admin
from app.models import Room, RoomType, User
from app.schemas.api import RoomTypeResponse, RoomTypeWriteRequest
from app.services import room_type_to_wire


router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


@router.get("/", response_model=list[RoomTypeResponse])
def get_room_types(db: Db):
    values = db.scalars(select(RoomType).order_by(RoomType.base_rate)).all()
    return [room_type_to_wire(value) for value in values]


@router.post("/", response_model=RoomTypeResponse, status_code=status.HTTP_201_CREATED)
def create_room_type(payload: RoomTypeWriteRequest, db: Db, _admin: Admin):
    if db.scalar(select(RoomType.id).where(func.lower(RoomType.name) == payload.name.lower())):
        problem(409, "A room type with that name already exists.")
    value = RoomType(
        name=payload.name,
        description=payload.description,
        max_occupancy=payload.max_occupancy,
        base_rate=payload.base_rate,
        amenities_json=json.dumps(payload.amenities),
        image_url=payload.image_url,
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    return room_type_to_wire(value)


@router.put("/{room_type_id}", response_model=RoomTypeResponse)
def update_room_type(room_type_id: int, payload: RoomTypeWriteRequest, db: Db, _admin: Admin):
    value = db.get(RoomType, room_type_id)
    if not value:
        problem(404, "We could not find that room type.")
    duplicate = db.scalar(select(RoomType.id).where(func.lower(RoomType.name) == payload.name.lower(), RoomType.id != room_type_id))
    if duplicate:
        problem(409, "A room type with that name already exists.")
    value.name = payload.name
    value.description = payload.description
    value.max_occupancy = payload.max_occupancy
    value.base_rate = payload.base_rate
    value.amenities_json = json.dumps(payload.amenities)
    value.image_url = payload.image_url
    db.commit()
    db.refresh(value)
    return room_type_to_wire(value)


@router.delete("/{room_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room_type(room_type_id: int, db: Db, _admin: Admin):
    value = db.get(RoomType, room_type_id)
    if not value:
        problem(404, "We could not find that room type.")
    if db.scalar(select(Room.id).where(Room.room_type_id == room_type_id).limit(1)):
        problem(409, "This room type is still assigned to rooms.")
    db.delete(value)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
