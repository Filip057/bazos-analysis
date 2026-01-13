from datetime import datetime
import re
import csv
import asyncio
from typing import Optional, Dict, List

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from database.model import Model, Brand, Offer, engine
import aiomysql


import os
from dotenv import load_dotenv

load_dotenv()
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')

# Define a test database URL
DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@localhost/bazos_cars'


# Scoped session configuration
Session = scoped_session(sessionmaker(bind=engine))

# Pre-compiled regex for unique_id extraction
UNIQUE_ID_PATTERN = re.compile(r'inzerat/(\d+)/')

# Lock for thread-safe CSV writing
csv_lock = asyncio.Lock()


"""
Here are functions that i use to operate with database, or somehow related to database
"""

# This fnc checks if the offer is PROBABLY a car offer
# trying to select data from tires, disc, car parts... 
def check_if_car(model, heading, price):
    if model == None:
        return False
    if price is None or price < 5000:
        return False
    non_car_keywords = [ 'ALU','kola' ,'kol' , 'motor','sada','díly', 'sklo', 'převodovka', 'pneu', 'pneumatiky', 'disky', 'sedadla', 'baterie', 'náhradní', 'zrcátka', 'motocykl', 'motorky', 'moto', 'kolo', 'kola', 
                        'skútr','motorové', 'karavany', 'choppery', 'endura', 'autobus', 'autodíly', 'zimní', 'letní',]
    
    non_car_pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, non_car_keywords)) + r')\b', re.IGNORECASE)
    
    # Check if any non-car keyword is present in the heading
    return not bool(non_car_pattern.search(heading))

def compute_derived_metrics(price, mileage, year_manufacture):
    current_year = datetime.now().year
    years_in_usage = current_year - year_manufacture if year_manufacture else None
    price_per_km = price / mileage if mileage and mileage > 0 else None
    mileage_per_year = mileage / years_in_usage if mileage and years_in_usage and years_in_usage > 0 else None
    return years_in_usage, price_per_km, mileage_per_year  

async def log_unknown_model(model: Optional[str], url: str, year_manufacture: Optional[int] = None,
                            mileage: Optional[int] = None, price: Optional[int] = None):
    """Async CSV logging for unknown models with thread safety"""
    async with csv_lock:
        file_exists = os.path.isfile('unknown_models.csv')
        # Use regular file I/O since aiofiles doesn't support csv module
        with open('unknown_models.csv', 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['Model', 'URL', 'Year Manufacture', 'Mileage', 'Price'])  # Header row
            writer.writerow([model, url, year_manufacture, mileage, price])  

# Cache for model lookups to avoid repeated database queries
_model_cache: Dict[tuple, Optional[int]] = {}


def get_model_id_sync(session, brand_name: str, model_name: Optional[str]) -> Optional[int]:
    """Synchronous model ID lookup with caching"""
    if not model_name:
        return None

    brand_name = brand_name.lower().strip()
    model_name = model_name.lower().strip()

    # Check cache first
    cache_key = (brand_name, model_name)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    # Query database
    brand = session.query(Brand).filter(Brand.name.ilike(brand_name)).first()

    if brand:
        model = session.query(Model).filter(Model.name.ilike(model_name), Model.brand_id == brand.id).first()
        if model:
            _model_cache[cache_key] = model.id
            return model.id

    _model_cache[cache_key] = None
    return None


async def fetch_data_into_database(data: List[Dict], batch_size: int = 100):
    """Optimized async database insertion with caching"""
    if not data:
        print("No data to save")
        return

    # Pre-load all model IDs in a single synchronous block to avoid blocking in async loop
    session = Session()
    try:
        model_lookup = {}
        unknown_models = []

        for item in data:
            brand = item['brand']
            model = item['model']
            key = (brand, model)

            if key not in model_lookup:
                model_id = get_model_id_sync(session, brand, model)
                model_lookup[key] = model_id

                if model_id is None and model is not None:
                    unknown_models.append({
                        'model': model,
                        'url': item['url'],
                        'year_manufacture': item.get('year_manufacture'),
                        'mileage': item.get('mileage'),
                        'price': item.get('price')
                    })

        # Log all unknown models asynchronously
        if unknown_models:
            await asyncio.gather(*[
                log_unknown_model(
                    um['model'], um['url'], um['year_manufacture'], um['mileage'], um['price']
                ) for um in unknown_models
            ])
    finally:
        session.close()

    # Now do async database inserts
    async with aiomysql.create_pool(
        host='localhost',
        user='root',
        password=os.getenv("MYSQL_PASSWORD"),
        db='bazos_cars',
        minsize=1,
        maxsize=10
    ) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                inserted_count = 0

                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    values = []

                    for item in batch:
                        # Use pre-compiled regex pattern
                        unique_id_match = UNIQUE_ID_PATTERN.search(item['url'])
                        unique_id = unique_id_match.group(1) if unique_id_match else None

                        years_in_usage, price_per_km, mileage_per_year = compute_derived_metrics(
                            item['price'], item['mileage'], item['year_manufacture']
                        )

                        # Use cached model_id
                        model_id = model_lookup.get((item['brand'], item['model']))

                        if model_id:
                            values.append(
                                (model_id, item['year_manufacture'], item['mileage'], item['power'],
                                 item['price'], item['url'], years_in_usage, price_per_km, mileage_per_year, unique_id)
                            )

                    if values:
                        sql = """
                        INSERT INTO offers (model_id, year_manufacture, mileage, power, price, url, years_in_usage, price_per_km, mileage_per_year, unique_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            year_manufacture = VALUES(year_manufacture),
                            mileage = VALUES(mileage),
                            power = VALUES(power),
                            price = VALUES(price),
                            years_in_usage = VALUES(years_in_usage),
                            price_per_km = VALUES(price_per_km),
                            mileage_per_year = VALUES(mileage_per_year)
                        """
                        await cur.executemany(sql, values)
                        inserted_count += len(values)

                await conn.commit()
                print(f"✓ Inserted/Updated {inserted_count} records in database")



 



