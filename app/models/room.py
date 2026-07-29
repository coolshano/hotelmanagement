from sqlalchemy import Column, Integer, String, ForeignKey
from app.database.database import Base


class Room(Base):

    __tablename__ = "rooms"


    id = Column(Integer, primary_key=True)

    number = Column(String(10))

    floor = Column(Integer)

    status = Column(String(50))

    room_type_id = Column(
        Integer,
        ForeignKey("room_types.id")
    )