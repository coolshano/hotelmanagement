from sqlalchemy import Column, Integer, String, Float
from app.database.database import Base


class RoomType(Base):

    __tablename__ = "room_types"


    id = Column(Integer, primary_key=True)

    name = Column(String(50))

    description = Column(String(200))

    price = Column(Float)