from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Float, Index, DateTime, Date, Text
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
        Index('idx_fuel', 'fuel'),
        Index('idx_scraped_at', 'scraped_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_id = Column(String(length=255), unique=True, nullable=True)
    model_id = Column(Integer, ForeignKey('models.id', ondelete='CASCADE'), nullable=False)
    year_manufacture = Column(Integer, nullable=True)
    mileage = Column(BigInteger, nullable=True)
    power = Column(Integer, nullable=True)
    fuel = Column(String(length=50), nullable=True)   # diesel | benzín | lpg | elektro
    price = Column(Integer, nullable=True)
    url = Column(String(length=255), nullable=True)
    scraped_at = Column(DateTime, nullable=True)       # When was this offer last seen
    listing_date = Column(Date, nullable=True)          # When the listing was created on bazos.cz
    view_count = Column(Integer, nullable=True)         # Number of views at time of scraping

    # Derived fields
    years_in_usage = Column(Integer, nullable=True)  # current_year - year_manufacture
    price_per_km = Column(Float, nullable=True)      # price / mileage
    mileage_per_year = Column(Float, nullable=True)  # mileage / years_in_usage

    # Review status: NULL (not reviewed), 'checked', 'dismissed'
    review_status = Column(String(length=20), nullable=True)

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
    fuel = Column(String(length=50))
    price = Column(Integer)
    url = Column(String(length=255))
    scraped_at = Column(DateTime)
    listing_date = Column(Date)
    view_count = Column(Integer)
    years_in_usage = Column(Integer)
    price_per_km = Column(Float)
    mileage_per_year = Column(Float)
    review_status = Column(String(length=20))

    def serialize(self):
        """Serialize car data to JSON"""
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year_manufacture': self.year_manufacture,
            'mileage': self.mileage,
            'power': self.power,
            'fuel': self.fuel,
            'price': self.price,
            'url': self.url,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'listing_date': self.listing_date.isoformat() if self.listing_date else None,
            'view_count': self.view_count,
            'years_in_usage': self.years_in_usage,
            'price_per_km': float(self.price_per_km) if self.price_per_km else None,
            'mileage_per_year': float(self.mileage_per_year) if self.mileage_per_year else None,
            'review_status': self.review_status,
        }

# Admin users (super admins with full access to admin endpoints)
class Admin(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(length=80), unique=True, nullable=False)
    password_hash = Column(String(length=255), nullable=False)
    created_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)


# Scraping job tracking (admin-triggered scrape sessions)
class ScrapeJob(Base):
    """Tracks scraping jobs triggered from the admin UI."""
    __tablename__ = 'scrape_jobs'
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_started_at', 'started_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(length=50), unique=True, nullable=False)
    status = Column(String(length=20), nullable=False, default='queued')
    brands = Column(Text, nullable=True)           # JSON array or "all"
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    current_brand = Column(String(length=50), nullable=True)
    brands_done = Column(Text, nullable=True)       # JSON array
    total_urls = Column(Integer, nullable=False, default=0)
    processed_urls = Column(Integer, nullable=False, default=0)
    saved_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    filtered_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    worker_pid = Column(Integer, nullable=True)

    def serialize(self) -> dict:
        """Serialize job to JSON-safe dict."""
        import json
        return {
            'job_id': self.job_id,
            'status': self.status,
            'brands': json.loads(self.brands) if self.brands else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'current_brand': self.current_brand,
            'brands_done': json.loads(self.brands_done) if self.brands_done else [],
            'total_urls': self.total_urls,
            'processed_urls': self.processed_urls,
            'saved_count': self.saved_count,
            'failed_count': self.failed_count,
            'filtered_count': self.filtered_count,
            'error_message': self.error_message,
        }


# ENGINE
engine = create_engine(DATABASE_URI)

# Don't connect immediately - only when actually needed
def init_database():
    """Initialize database tables - call this when you actually need the database"""
    Base.metadata.create_all(engine)