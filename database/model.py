from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Float, Index
from sqlalchemy import create_engine
from webapp.config import get_config

# Load configuration
config = get_config()
DATABASE_URI = config.DATABASE_URI

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
    __table_args__ = (
        Index('idx_model_id', 'model_id'),
        Index('idx_price', 'price'),
        Index('idx_year_manufacture', 'year_manufacture'),
        Index('idx_mileage', 'mileage'),
        Index('idx_unique_id', 'unique_id'),
    )

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


# Flattened Car model for API compatibility (backward compatible)
class Car(Base):
    __tablename__ = 'car_view'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    brand = Column(String(length=100))
    model = Column(String(length=100))
    year_manufacture = Column(Integer)
    mileage = Column(BigInteger)
    power = Column(Integer)
    price = Column(Integer)
    url = Column(String(length=255))
    years_in_usage = Column(Integer)
    price_per_km = Column(Float)
    mileage_per_year = Column(Float)

    def serialize(self):
        """Serialize car data to JSON"""
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year_manufacture': self.year_manufacture,
            'mileage': self.mileage,
            'power': self.power,
            'price': self.price,
            'url': self.url,
            'years_in_usage': self.years_in_usage,
            'price_per_km': float(self.price_per_km) if self.price_per_km else None,
            'mileage_per_year': float(self.mileage_per_year) if self.mileage_per_year else None
        }

# ENGINE
engine = create_engine(DATABASE_URI)

# Don't connect immediately - only when actually needed
# connection = engine.connect()  # Removed - connects lazily now

# Create the tables in the database (only if connected)
Base.metadata.create_all(engine)