from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.database.database import get_db
from app.dependencies import require_admin
from app.models import Guest, User
from app.schemas.api import GuestResponse, GuestWriteRequest


router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


def _wire(guest: Guest) -> dict[str, object]:
    return {
        "id": guest.id, 
        "first_name": guest.first_name, 
        "last_name": guest.last_name, 
        "phone": guest.phone, 
        "email": guest.email, 
        "address": guest.address
    }


@router.get("/", response_model=list[GuestResponse])
@cache(expire=3600, namespace="guests")
def list_guests(db: Db, _admin: Admin):
    return [_wire(guest) for guest in db.scalars(select(Guest).order_by(Guest.last_name)).all()]


@router.post("/", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
async def create_guest(payload: GuestWriteRequest, db: Db, _admin: Admin):
    if db.scalar(select(Guest.id).where(func.lower(Guest.email) == payload.email)):
        problem(409, "A guest with that email already exists.")
    
    guest = Guest(**payload.model_dump())
    db.add(guest)
    db.commit()
    db.refresh(guest)
    
    # Invalidate the cache so the next GET request fetches fresh data
    await FastAPICache.clear(namespace="guests")
    
    return _wire(guest)


@router.get("/{guest_id}", response_model=GuestResponse)
@cache(expire=3600, namespace="guests")
def get_guest(guest_id: int, db: Db, _admin: Admin):
    guest = db.get(Guest, guest_id)
    if not guest:
        problem(404, "We could not find that guest.")
    return _wire(guest)


@router.put("/{guest_id}", response_model=GuestResponse)
async def update_guest(guest_id: int, payload: GuestWriteRequest, db: Db, _admin: Admin):
    guest = db.get(Guest, guest_id)
    if not guest:
        problem(404, "We could not find that guest.")
        
    for field, value in payload.model_dump().items():
        setattr(guest, field, value)
        
    db.commit()
    db.refresh(guest)
    
    # Invalidate the cache so the updated guest details appear immediately
    await FastAPICache.clear(namespace="guests")
    
    return _wire(guest)


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest(guest_id: int, db: Db, _admin: Admin):
    guest = db.get(Guest, guest_id)
    if not guest:
        problem(404, "We could not find that guest.")
        
    db.delete(guest)
    db.commit()
    
    # Invalidate the cache so the deleted guest is removed from the list
    await FastAPICache.clear(namespace="guests")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)