import pytest
import os
import sys

from database_operations import save_to_csv, fetch_data_into_database


from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine
from app import Car

from database.model import Base

sys.path.append('/Users/filiphome/bazos analysis')

@pytest.fixture
def sample_data():
    # Create a sample data list for testing
    return [
        {"brand": "mazda", "model": "6", "year_manufacture": 2018, "mileage": 58000, "power": 120, "price": 799900, "heading": "Mazda CX 3, 2022, 8 tis.km"},
        {"brand": "mazda", "model": "CX-3", "year_manufacture": 2015, "mileage": None, "power": 143, "price": 695000, "heading": "Mazda CX-5, AWD, 2.5 SkyActive-G, AT, REVOL.TOP, 1. majitel"},
        # Add more sample data here
    ]


def test_save_to_csv(sample_data):
    # Test save_to_csv function
    filename = "test_data.csv"
    save_to_csv(sample_data, filename)
    assert os.path.exists(filename)
    # os.remove(filename)  # Cleanup after the test

def test_fetch_data_into_database(sample_data):
    # Create a test engine and session
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create tables in the test database
    Base.metadata.create_all(bind=engine)
    
    session = None
    try:
        # Call fetch_data_into_database to insert data into the test database
        fetch_data_into_database(sample_data)

        # Create a session to query the database
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        # Query the database to check if the data is correctly inserted
        saved_cars = session.query(Car).all()

        # Check if the number of saved cars matches the number of sample data
        assert len(saved_cars) == len(sample_data)

        # Optionally, you can check other properties of the saved cars

    finally:
        # Close the session and remove the test database
        if session:
            session.close()
        os.remove('test_bazos_cars.db')
        