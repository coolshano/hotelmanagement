from sqlalchemy import Column, Integer, String, ForeignKey
from app.database.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    username = Column(String(100))

    email = Column(String(100), unique=True)

    password = Column(String(255))

    role_id = Column(
        Integer,
        ForeignKey("roles.id")
    )