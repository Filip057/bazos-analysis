from datetime import datetime
import re
import csv

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

def log_unknown_model(model, url, year_manufacture=None, mileage=None, price=None):
    # Save to a CSV file for unknown models
    file_exists = os.path.isfile('unknown_models.csv')
    with open('unknown_models.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['Model', 'URL', 'Year Manufacture', 'Mileage', 'Price'])  # Header row
        writer.writerow([model, url, year_manufacture, mileage, price])  

def get_model_id(session, brand_name, model_name, url=None, year_manufacture=None, mileage=None, price=None):
    brand_name = brand_name.lower().strip()
    model_name = model_name.lower().strip() if model_name else None
    brand = session.query(Brand).filter(Brand.name.ilike(brand_name)).first()

    if brand and model_name:
        model = session.query(Model).filter(Model.name.ilike(model_name), Model.brand_id == brand.id).first()
        if model:
            return model.id

    # Log unknown model to a CSV file
    log_unknown_model(model_name, url, year_manufacture, mileage, price)
    return None

async def fetch_data_into_database(data, batch_size=100):
    async with aiomysql.create_pool(host='localhost', user='root', password=os.getenv("MYSQL_PASSWORD"), db='bazos_cars') as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Create a session to interact with the database
                session = Session()  # Add a session here
                
                for i in range(0, len(data), batch_size):
                    batch = data[i:i+batch_size]
                    values = []
                    for item in batch:
                        unique_id = re.search(r'inzerat/(\\d+)/', item['url'])
                        unique_id = unique_id.group(1) if unique_id else None
                        years_in_usage, price_per_km, mileage_per_year = compute_derived_metrics(
                            item['price'], item['mileage'], item['year_manufacture']
                        )
                        # Pass the session and all required arguments to get_model_id
                        model_id = get_model_id(
                            session, 
                            item['brand'], 
                            item['model'], 
                            url=item['url'], 
                            year_manufacture=item['year_manufacture'], 
                            mileage=item['mileage'], 
                            price=item['price']
                        )
                        if model_id:
                            values.append(
                                (model_id, item['year_manufacture'], item['mileage'], item['power'],
                                 item['price'], item['url'], years_in_usage, price_per_km, mileage_per_year, unique_id)
                            )
                    if values:
                        sql = """
                        INSERT INTO offers (model_id, year_manufacture, mileage, power, price, url, years_in_usage, price_per_km, mileage_per_year, unique_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        await cur.executemany(sql, values)
                await conn.commit()
                
                # Close the session after use
                session.close()



 



