import re
import asyncio

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import aiomysql

from app import Car

import os
from dotenv import load_dotenv

load_dotenv()
MYSQL_USER = 'root'
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')

# Define a test database URL
DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@localhost/bazos_cars'

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
    is_car = not bool(non_car_pattern.search(heading))

    return is_car



# fnc that is responsible co adding data into database
async def fetch_data_into_database(data):
    async with aiomysql.create_pool(host='localhost', user='root', password=os.getenv("MYSQL_PASSWORD"), db='bazos_cars') as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                for item in data:
                    sql = "INSERT INTO cars (brand, model, year_manufacture, mileage, power, price) VALUES (%s, %s, %s, %s, %s, %s)"
                    await cur.execute(sql, (item['brand'], item['model'], item['year_manufacture'], item['mileage'], item['power'], item['price']))
                await conn.commit()
        


 



