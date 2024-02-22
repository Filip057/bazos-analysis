from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, BigInteger
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

class Car(Base):
    __tablename__ = 'cars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(length=50))
    model = Column(String(length=50))
    year_manufacture = Column(Integer, nullable=True)
    mileage = Column(BigInteger, nullable=True)
    power = Column(Integer, nullable=True)
    price = Column(Integer, nullable=True)

    def serialize(self):
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year_manufacture': self.year_manufacture,
            'mileage': self.mileage,
            'power': self.power,
            'price': self.price
        }

# ENGINE
engine = create_engine(DATABASE_URI)

connection = engine.connect()

# Create the tables in the database
Base.metadata.create_all(engine)