from datetime import datetime

from sqlalchemy import Column, Integer, String, DATE, ForeignKey
from sqlalchemy.orm import DeclarativeBase

NULLABLE = {'nullable': True}


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=True)
    created_at = Column(DATE, default=datetime.now())


class Product(Base):
    __tablename__ = 'products'

    article_id = Column(Integer, primary_key=True, nullable=False, index=True)
    name = Column(String, **NULLABLE)
    price = Column(Integer, **NULLABLE)
    sale = Column(String, **NULLABLE)
    brand = Column(String, **NULLABLE)
    rating = Column(String, **NULLABLE)
    supplier = Column(String, **NULLABLE)
    supplierRating = Column(String, **NULLABLE)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
