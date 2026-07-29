from sqlalchemy import Column, Integer, Date, String, ForeignKey
from app.database.database import Base


class Booking(Base):

    __tablename__ = "bookings"


    id = Column(Integer, primary_key=True)

    guest_id = Column(
        Integer,
        ForeignKey("guests.id")
    )


    room_id = Column(
        Integer,
        ForeignKey("rooms.id")
    )


    check_in = Column(Date)

    check_out = Column(Date)

    status = Column(String(50))