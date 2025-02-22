import os
from sqlalchemy.orm import sessionmaker
from database.model import Brand, Model, engine  # Import your SQLAlchemy models
from car_models import CAR_MODELS  # Import the brand-model dictionary

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Insert brands
brand_objects = {}
for brand_name in CAR_MODELS.keys():
    brand = Brand(name=brand_name)
    session.add(brand)
    brand_objects[brand_name] = brand  # Store brand objects to link models

# Commit brands first (so models can reference them)
session.commit()

# Insert models
for brand_name, models in CAR_MODELS.items():
    brand = brand_objects[brand_name]  # Get the inserted brand object
    for model_name in models:
        model = Model(name=model_name, brand_id=brand.id)
        session.add(model)

# Commit all models
session.commit()

print("Database populated with brands and models successfully!")
