from datetime import datetime, timezone
from typing import Annotated
import logging
import secrets

from anyio import to_thread
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.core.security import (
    decode_token,
    hash_password,
    issue_session,
    verify_password,
)
from app.database.database import get_db
from app.dependencies import get_current_user
from app.models import BiometricCredential, RefreshSession, User
from app.schemas.api import (
    AuthSessionResponse,
    BiometricDeviceResponse,
    BiometricEnrollRequest,
    BiometricEnrollResponse,
    BiometricLoginRequest,
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
from app.services import biometric_to_wire, user_to_wire
from app.notifications import send_welcome_email


router = APIRouter()

logger = logging.getLogger(__name__)

Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# Every timestamp column in this project stores naive UTC.
BIOMETRIC_REJECTED = (
    "Biometric sign-in is not available on this device. "
    "Please sign in with your password."
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post(
    "/login",
    response_model=AuthSessionResponse,
)
def login(payload: LoginRequest, db: Db):
    email = payload.email.strip().lower()

    user = db.scalar(
        select(User).where(
            func.lower(User.email) == email
        )
    )

    if not user or not verify_password(
        payload.password,
        user.password_hash,
    ):
        problem(
            401,
            "That email and password do not match.",
        )

    if user.status == "SUSPENDED":
        problem(
            403,
            "This account has been suspended. "
            "Contact the front desk for help.",
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
async def register(
    payload: RegisterRequest,
    db: Db,
):
    email = payload.email.strip().lower()

    # Check whether the email is already registered.
    if db.scalar(
        select(User.id).where(
            func.lower(User.email) == email
        )
    ):
        problem(
            409,
            "An account already exists for that email.",
            {
                "email": (
                    "This email is already registered."
                )
            },
        )

    user = User(
        email=email,
        full_name=payload.full_name,
        phone=payload.phone or None,
        password_hash=hash_password(
            payload.password
        ),
        role="REGISTERED_USER",
        status="ACTIVE",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Send welcome email after the database transaction
    # has successfully committed.
    #
    # Gmail SMTP is blocking, so run it in a worker thread.
    #
    # Email failure should NOT cause registration to fail.
    try:
        await to_thread.run_sync(
            send_welcome_email,
            user,
        )
    except Exception:
        logger.exception(
            "Failed to send welcome email to %s",
            user.email,
        )

    return {
        **issue_session(db, user),
        "user": user_to_wire(user),
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    payload: RefreshRequest,
    db: Db,
):
    claims = decode_token(
        payload.refresh_token,
        "refresh",
    )

    jti = str(claims["jti"])

    refresh_session = db.scalar(
        select(RefreshSession).where(
            RefreshSession.jti == jti
        )
    )

    now = datetime.now(
        timezone.utc
    ).replace(tzinfo=None)

    if (
        not refresh_session
        or refresh_session.revoked_at
        or refresh_session.expires_at <= now
    ):
        problem(
            401,
            "Your session has expired. "
            "Please sign in again.",
        )

    user = db.get(
        User,
        refresh_session.user_id,
    )

    if not user or user.status != "ACTIVE":
        problem(
            401,
            "Your session has expired. "
            "Please sign in again.",
        )

    refresh_session.revoked_at = now

    return issue_session(
        db,
        user,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    payload: LogoutRequest,
    db: Db,
):
    if payload.refresh_token:
        try:
            claims = decode_token(
                payload.refresh_token,
                "refresh",
            )

            refresh_session = db.scalar(
                select(RefreshSession).where(
                    RefreshSession.jti
                    == str(claims["jti"])
                )
            )

            if (
                refresh_session
                and not refresh_session.revoked_at
            ):
                refresh_session.revoked_at = (
                    datetime.now(
                        timezone.utc
                    ).replace(tzinfo=None)
                )

                db.commit()

        except Exception:
            db.rollback()

    return {
        "message": "Logged out"
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: CurrentUser,
):
    return user_to_wire(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: CurrentUser,
    db: Db,
):
    current_user.full_name = payload.full_name
    current_user.phone = payload.phone or None

    db.commit()
    db.refresh(current_user)

    return user_to_wire(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Db,
):
    if not verify_password(
        payload.current_password,
        current_user.password_hash,
    ):
        problem(
            400,
            "Your current password is not correct.",
            {
                "current_password": (
                    "Incorrect password."
                )
            },
        )

    current_user.password_hash = hash_password(
        payload.new_password
    )

    now = _now()

    db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id
            == current_user.id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )

    # A new password invalidates every enrolled biometric device too, so a
    # stolen phone cannot outlive a password reset.
    db.execute(
        update(BiometricCredential)
        .where(
            BiometricCredential.user_id
            == current_user.id,
            BiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )

    db.commit()

    return {
        "message": "Password changed" }


# ---------------------------------------------------------------- biometrics
#
# Enrolment mints a random secret, hands the plaintext to the device exactly
# once and keeps only its PBKDF2 hash. The device stores it behind the OS
# keystore, so reading it back requires the user's fingerprint or face.
#
# Because the enrolment lives here rather than only on the phone, an admin can
# revoke it from the web app and the device loses biometric access immediately.


def _active_credentials(user_id: int):
    return select(BiometricCredential).where(
        BiometricCredential.user_id == user_id,
        BiometricCredential.revoked_at.is_(None),
    )


@router.post(
    "/biometric/enroll",
    response_model=BiometricEnrollResponse,
    status_code=status.HTTP_201_CREATED,
)
def enroll_biometric(
    payload: BiometricEnrollRequest,
    current_user: CurrentUser,
    db: Db,
):
    if current_user.role != "ADMIN":
        problem(
            403,
            "Biometric sign-in is only available for administrator accounts.",
        )

    secret = secrets.token_urlsafe(32)

    # Re-enrolling the same device replaces the old secret rather than piling
    # up rows, and un-revokes a device an admin had previously reset.
    credential = db.scalar(
        select(BiometricCredential).where(
            BiometricCredential.user_id == current_user.id,
            BiometricCredential.device_id == payload.device_id,
        )
    )

    if credential:
        credential.secret_hash = hash_password(secret)
        credential.device_label = payload.device_label
        credential.created_at = _now()
        credential.last_used_at = None
        credential.revoked_at = None
    else:
        credential = BiometricCredential(
            user_id=current_user.id,
            device_id=payload.device_id,
            device_label=payload.device_label,
            secret_hash=hash_password(secret),
        )
        db.add(credential)

    db.commit()
    db.refresh(credential)

    return {
        **biometric_to_wire(credential),
        "biometric_token": secret,
    }


@router.post(
    "/biometric/login",
    response_model=AuthSessionResponse,
)
def biometric_login(
    payload: BiometricLoginRequest,
    db: Db,
):
    user = db.scalar(
        select(User).where(func.lower(User.email) == payload.email)
    )

    credential = (
        db.scalar(
            _active_credentials(user.id).where(
                BiometricCredential.device_id == payload.device_id
            )
        )
        if user
        else None
    )

    # One message for every failure mode - a wrong secret, a device an admin
    # has reset, a suspended account, a demoted admin - so this endpoint can
    # not be used to probe which accounts exist or which devices are enrolled.
    if (
        not user
        or not credential
        or not verify_password(payload.biometric_token, credential.secret_hash)
        or user.status != "ACTIVE"
        or user.role != "ADMIN"
    ):
        problem(401, BIOMETRIC_REJECTED)

    credential.last_used_at = _now()

    return {
        **issue_session(db, user),
        "user": user_to_wire(user),
    }


@router.get(
    "/biometric/devices",
    response_model=list[BiometricDeviceResponse],
)
def list_biometric_devices(
    current_user: CurrentUser,
    db: Db,
):
    credentials = db.scalars(
        _active_credentials(current_user.id).order_by(
            BiometricCredential.created_at.desc()
        )
    ).all()

    return [biometric_to_wire(credential) for credential in credentials]


@router.delete(
    "/biometric/devices/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_biometric_device(
    credential_id: int,
    current_user: CurrentUser,
    db: Db,
):
    credential = db.scalar(
        _active_credentials(current_user.id).where(
            BiometricCredential.id == credential_id
        )
    )

    if not credential:
        problem(404, "We could not find that device.")

    credential.revoked_at = _now()
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/biometric",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reset_own_biometric(
    current_user: CurrentUser,
    db: Db,
):
    db.execute(
        update(BiometricCredential)
        .where(
            BiometricCredential.user_id == current_user.id,
            BiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
