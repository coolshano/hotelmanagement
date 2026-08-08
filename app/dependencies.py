from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.core.security import decode_token
from app.database.database import get_db
from app.models import User

from redis.asyncio import Redis
from app.core.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not token:
        problem(401, "You need to sign in to continue.")
    claims = decode_token(token, "access")
    try:
        user_id = int(str(claims["sub"]))
    except (KeyError, TypeError, ValueError):
        problem(401, "Your session has expired. Please sign in again.")
    user = db.get(User, user_id)
    if not user:
        problem(401, "Your session has expired. Please sign in again.")
    if user.status == "SUSPENDED":
        problem(403, "This account has been suspended. Contact the front desk for help.")
    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "ADMIN":
        problem(403, "You do not have permission to perform this action.")
    return current_user


async def get_redis() -> Redis:
    redis = Redis.from_url(
        settings.REDIS_URL, 
        encoding="utf8", 
        decode_responses=True
    )
    try:
        yield redis
    finally:
        await redis.aclose()
