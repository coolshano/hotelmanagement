from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import problem
from app.models import RefreshSession, User


ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 390_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_encoded, digest_encoded = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_encoded.encode())
        expected = base64.urlsafe_b64decode(digest_encoded.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def _create_token(user_id: int, token_type: str, lifetime: timedelta) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + lifetime
    jti = uuid4().hex
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": token_type,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    return token, jti, expires_at.replace(tzinfo=None)


def create_access_token(user_id: int) -> str:
    token, _, _ = _create_token(
        user_id, "access", timedelta(minutes=settings.access_token_minutes)
    )
    return token


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_days))


def decode_token(token: str, expected_type: str) -> dict[str, object]:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        problem(401, "Your session has expired. Please sign in again.")
    if claims.get("type") != expected_type or not claims.get("sub") or not claims.get("jti"):
        problem(401, "Your session has expired. Please sign in again.")
    return claims


def issue_session(db: Session, user: User) -> dict[str, object]:
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    db.add(RefreshSession(jti=jti, user_id=user.id, expires_at=expires_at))
    db.commit()
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_minutes * 60,
    }

