from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.core.security import decode_token, hash_password, issue_session, verify_password
from app.database.database import get_db
from app.dependencies import get_current_user
from app.models import RefreshSession, User
from app.schemas.api import (
    AuthSessionResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import user_to_wire


router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/login", response_model=AuthSessionResponse)
def login(payload: LoginRequest, db: Db):
    email = payload.email.strip().lower()

    user = db.scalar(
        select(User).where(func.lower(User.email) == email)
    )

    if not user or not verify_password(
        payload.password,
        user.password_hash,
    ):
        problem(401, "That email and password do not match.")

    if user.status == "SUSPENDED":
        problem(
            403,
            "This account has been suspended. Contact the front desk for help.",
        )

    return {
        **issue_session(db, user),
        "user": user_to_wire(user),
    }

@router.post(
    "/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: Db):
    email = payload.email.strip().lower()

    if db.scalar(
        select(User.id).where(func.lower(User.email) == email)
    ):
        problem(
            409,
            "An account already exists for that email.",
            {"email": "This email is already registered."},
        )

    user = User(
        email=email,
        full_name=payload.full_name,
        phone=payload.phone or None,
        password_hash=hash_password(payload.password),
        role="REGISTERED_USER",
        status="ACTIVE",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        **issue_session(db, user),
        "user": user_to_wire(user),
    }
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Db):
    claims = decode_token(payload.refresh_token, "refresh")
    jti = str(claims["jti"])
    refresh_session = db.scalar(select(RefreshSession).where(RefreshSession.jti == jti))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if not refresh_session or refresh_session.revoked_at or refresh_session.expires_at <= now:
        problem(401, "Your session has expired. Please sign in again.")
        
    user = db.get(User, refresh_session.user_id)
    if not user or user.status != "ACTIVE":
        problem(401, "Your session has expired. Please sign in again.")
        
    refresh_session.revoked_at = now
    return issue_session(db, user)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, db: Db):
    if payload.refresh_token:
        try:
            claims = decode_token(payload.refresh_token, "refresh")
            refresh_session = db.scalar(select(RefreshSession).where(RefreshSession.jti == str(claims["jti"])))
            if refresh_session and not refresh_session.revoked_at:
                refresh_session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser):
    return user_to_wire(current_user)


@router.patch("/me", response_model=UserResponse)
def update_profile(payload: ProfileUpdateRequest, current_user: CurrentUser, db: Db):
    current_user.full_name = payload.full_name
    current_user.phone = payload.phone or None
    db.commit()
    db.refresh(current_user)
    return user_to_wire(current_user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, db: Db):
    if not verify_password(payload.current_password, current_user.password_hash):
        problem(400, "Your current password is not correct.", {"current_password": "Incorrect password."})
        
    current_user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == current_user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()
    
    return {"message": "Password changed"}