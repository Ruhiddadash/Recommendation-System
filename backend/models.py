from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    email = Column(String(120), unique=True)
    password = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    selections = relationship("UserMovieSelection", back_populates="user")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    title = Column(String(180), unique=True)
    genre = Column(String(200))
    rating = Column(String(10))


class UserMovieSelection(Base):
    __tablename__ = "user_movie_selection"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_title = Column(String(180))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="selections")
