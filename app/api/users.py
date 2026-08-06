from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.core.security import hash_password
from app.database.database import get_db
from app.dependencies import require_admin
from app.models import Booking, User
from app.schemas.api import UserCreateRequest, UserResponse, UserUpdateRequest
from app.services import ACTIVE_BOOKING_STATUSES, user_to_wire


router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


@router.get("/", response_model=list[UserResponse])
def get_users(db: Db, _admin: Admin):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [user_to_wire(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Db, _admin: Admin):
    user = db.get(User, user_id)
    if not user:
        problem(404, "We could not find that user.")
    return user_to_wire(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest, db: Db, _admin: Admin):
    if db.scalar(select(User.id).where(func.lower(User.email) == payload.email)):
        problem(409, "An account already exists for that email address.", {"email": "This email is already registered."})
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone or None,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status="ACTIVE",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_wire(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdateRequest, db: Db, admin: Admin):
    user = db.get(User, user_id)
    if not user:
        problem(404, "We could not find that user.")
    if admin.id == user_id and payload.role != "ADMIN":
        problem(409, "You cannot remove your own administrator access.")
    if admin.id == user_id and payload.status != "ACTIVE":
        problem(409, "You cannot suspend the account you are signed in with.")
    user.full_name = payload.full_name
    user.phone = payload.phone or None
    user.role = payload.role
    user.status = payload.status
    db.commit()
    db.refresh(user)
    return user_to_wire(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Db, admin: Admin):
    if admin.id == user_id:
        problem(409, "You cannot delete the account you are signed in with.")
    user = db.get(User, user_id)
    if not user:
        problem(404, "We could not find that user.")
    if db.scalar(select(Booking.id).where(Booking.user_id == user_id).limit(1)):
        problem(409, "This user has booking history and cannot be deleted. Suspend the account instead.")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
