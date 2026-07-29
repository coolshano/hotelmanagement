from fastapi import FastAPI

from app.api import (
    auth,
    users,
    guests,
    room_types,
    rooms,
    bookings,
    payments,
    reports
)


app = FastAPI(
    title="Hotel Management System API",
    version="1.0"
)


app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

app.include_router(
    guests.router,
    prefix="/guests",
    tags=["Guests"]
)

app.include_router(
    room_types.router,
    prefix="/room-types",
    tags=["Room Types"]
)

app.include_router(
    rooms.router,
    prefix="/rooms",
    tags=["Rooms"]
)

app.include_router(
    bookings.router,
    prefix="/bookings",
    tags=["Bookings"]
)

app.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"]
)

app.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"]
)


@app.get("/health")
def health():
    return {
        "status":"UP"
    }