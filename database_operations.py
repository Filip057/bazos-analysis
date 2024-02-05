from app import db
from models import CarBrand, BrandModel, ModelInstance

import re

def check_if_car(car_data):
    
    heading = car_data['heading']

    non_car_keywords = [ 'ALU','kola' ,'kol' ,'sada','díly', 'sklo', 'pneu', 'pneumatiky', 'disky', 'sedadla', 'baterie', 'náhradní', 'zrcátka', 'motocykl', 'motorky', 'moto', 'kolo', 'kola', 
                        'skútr','motorové', 'karavany', 'choppery', 'endura', 'autobus', 'autodíly', 'zimní', 'letní',]
    
    non_car_pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, non_car_keywords)) + r')\b', re.IGNORECASE)
    
    # Check if any non-car keyword is present in the heading
    is_car = not bool(non_car_pattern.search(heading))

    return is_car

def add_car_data(car_data):
    """
    Add car data to the database.
    """
    # Extract data from car_data dictionary
    brand_name = car_data["brand"]
    model_name = car_data["model"]
    year_manufacture = car_data["year_manufacture"]
    mileage = car_data["mileage"]
    power = car_data["power"]
    price = car_data["price"]

    # Check if the brand already exists in the database
    brand = CarBrand.query.filter_by(brand=brand_name).first()
    if not brand:
        # If the brand doesn't exist, create a new one
        brand = CarBrand(brand=brand_name)
        db.session.add(brand)
        db.session.commit()

    # Check if the model already exists in the database
    model = BrandModel.query.filter_by(model=model_name, brand_id=brand.id).first()
    if not model:
        # If the model doesn't exist, create a new one
        model = BrandModel(model=model_name, brand_id=brand.id)
        db.session.add(model)
        db.session.commit()

    # Add the model instance to the database
    instance = ModelInstance(year_manufacture=year_manufacture, mileage=mileage, power=power, price=price, model_id=model.id)
    db.session.add(instance)
    db.session.commit()


