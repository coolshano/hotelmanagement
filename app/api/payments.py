from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import problem
from app.database.database import get_db
from app.dependencies import require_admin
from app.models import Booking, Payment, User
from app.schemas.api import PaymentCreateRequest, PaymentResponse
from app.services import payment_to_wire


router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


@router.get("/", response_model=list[PaymentResponse])
def payments(db: Db, _admin: Admin):
    values = db.scalars(select(Payment).order_by(Payment.paid_at.desc())).all()
    return [payment_to_wire(value) for value in values]


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreateRequest, db: Db, _admin: Admin):
    if not db.get(Booking, payload.booking_id):
        problem(404, "We could not find that booking.")
    value = Payment(
        booking_id=payload.booking_id,
        amount=payload.amount,
        currency=payload.currency.upper(),
        method=payload.method,
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    return payment_to_wire(value)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Db, _admin: Admin):
    value = db.get(Payment, payment_id)
    if not value:
        problem(404, "We could not find that payment.")
    return payment_to_wire(value)
