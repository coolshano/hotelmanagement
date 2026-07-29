from sqlalchemy import Column, Integer, Float, String, ForeignKey
from app.database.database import Base


class Payment(Base):

    __tablename__ = "payments"


    id = Column(Integer, primary_key=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id")
    )


    amount = Column(Float)

    method = Column(String(50))

    paid_date = Column(String(50))