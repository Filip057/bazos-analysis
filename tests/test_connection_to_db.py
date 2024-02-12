from sqlalchemy import create_engine
import pytest

from sqlalchemy import create_engine

@pytest.fixture(scope='module')
def db_engine():
    # Create a test database engine
    engine = create_engine('sqlite:///bazos_cars.db')
    yield engine
    engine.dispose()  # Clean up the engine after the test

def test_database_connection(db_engine):
    with db_engine.connect() as connection:
        result = connection.execute('SELECT 1')
        assert result.scalar() == 1