from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Float
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')

# MySQL connection string
DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@localhost/bazos_cars'

# CLASSES 
class Base(DeclarativeBase):
    pass
# table with all brands
class Brand(Base):
    __tablename__ = 'brands'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(length=100), unique=True, nullable=False)

    models = relationship('Model', back_populates='brand', cascade='all, delete')

# table with all models of each brand
class Model(Base):
    __tablename__ = 'models'

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(length=100), nullable=False)

    brand = relationship('Brand', back_populates='models')
    offers = relationship('Offer', back_populates='model', cascade='all, delete')

# table with all offers of each model
class Offer(Base):
    __tablename__ = 'offers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_id = Column(String(length=255), unique=True, nullable=True)
    model_id = Column(Integer, ForeignKey('models.id', ondelete='CASCADE'), nullable=False)
    year_manufacture = Column(Integer, nullable=True)
    mileage = Column(BigInteger, nullable=True)
    power = Column(Integer, nullable=True)
    price = Column(Integer, nullable=True)
    url = Column(String(length=255), nullable=True)

    # Derived fields
    years_in_usage = Column(Integer, nullable=True)  # 2025 - year_manufacture
    price_per_km = Column(Float, nullable=True)  # price / mileage
    mileage_per_year = Column(Float, nullable=True)  # mileage / years_in_usage
    
    # relationships
    model = relationship('Model', back_populates='offers')

# ENGINE
engine = create_engine(DATABASE_URI)

connection = engine.connect()

# Create the tables in the database
Base.metadata.create_all(engine)