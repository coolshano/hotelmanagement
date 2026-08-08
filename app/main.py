from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.api import (
    auth,
    users,
    guests,
    room_types,
    rooms,
    bookings,
    payments,
    reports,
)
from app.core.config import settings
from app.database.database import initialize_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()

    redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    FastAPICache.init(
        RedisBackend(redis),
        prefix="hotel-management-cache",
    )

    yield

    await redis.close()


app = FastAPI(
    title="Hotel Management System API",
    version="2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

app.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

app.include_router(
    guests.router,
    prefix="/guests",
    tags=["Guests"],
)

app.include_router(
    room_types.router,
    prefix="/room-types",
    tags=["Room Types"],
)

app.include_router(
    rooms.router,
    prefix="/rooms",
    tags=["Rooms"],
)

app.include_router(
    rooms.availability_router,
    tags=["Availability"],
)

app.include_router(
    bookings.router,
    prefix="/bookings",
    tags=["Bookings"],
)

app.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"],
)

app.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)


@app.get("/health")
def health():
    return {"status": "UP"}