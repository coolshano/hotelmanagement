from sqlalchemy import Column, Integer, String
from app.database.database import Base


class Guest(Base):

    __tablename__ = "guests"

    id = Column(Integer, primary_key=True)

    first_name = Column(String(50))

    last_name = Column(String(50))

    phone = Column(String(20))

    email = Column(String(100))

    address = Column(String(200))