import pytest
import sys
sys.path.append('/Users/filiphome')

from  database_operations import check_if_car

@pytest.mark.parametrize("heading, expected_result", [
    ("Mazda 3 2.0i e-SKYACTIV G-122 PLUSTOP benzín manuál 90 kw", True),  # Example of a car heading
    ("Díly Mazda 323F BG", False),  # Example of a non-car heading
    ("Kola +gumy + hagusy ", False),
    ('Kompletní sada kol Mazda 5 R15', False),
    ('Mazda 6, r.v. 2005 - náhradní díly', False)
    # Add more test cases as needed

])

def test_check_if_car(heading, expected_result):
    car_data = {'heading': heading}
    assert check_if_car(car_data) == expected_result