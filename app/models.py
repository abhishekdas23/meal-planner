from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Text, nullable=False)
    meal_time = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    portion = Column(Text, nullable=False)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(Text, nullable=False)


class Household(Base):
    __tablename__ = "household"

    id = Column(Integer, primary_key=True)
    pin_hash = Column(Text, nullable=False)
