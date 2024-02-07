import re
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app import Car, Base
import csv

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


import csv
# fnc to save data from web scrap into csv
def save_to_csv(data, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


# reading data from csv
def read_csv(filename):
    data = []
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)
    return data


# fnc that is responsible co adding data into database
def fetch_data_into_database(data):
    engine = create_engine('sqlite:///bazos_cars.db', pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    
    
    with SessionLocal() as session: 
        try:
            for item in data:
                i = 1
                car = Car(
                    _id=i,
                    brand=item['brand'],
                    model=item['model'],
                    year_manufacture=item['year_manufacture'],
                    mileage=item['mileage'],
                    power=item['power'],
                    price=item['price'],
                )
                session.add(car)
                i += 1
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
    
# test data
SAMPLEDATA = [
    {"brand": "mazda", "model": "3", "year_manufacture": 2022, "mileage": 8000, "power": None, "price": 499900, "heading": "Mazda CX 3, 2022, 8 tis.km"},
    {"brand": "mazda", "model": "CX-5", "year_manufacture": 2018, "mileage": None, "power": 143, "price": 595000, "heading": "Mazda CX-5, AWD, 2.5 SkyActive-G, AT, REVOL.TOP, 1. majitel"},
]

if __name__ == "__main__":
    # test of insertion 
    filename = 'test_data.csv'
    data = read_csv(filename)
    fetch_data_into_database(data)  



