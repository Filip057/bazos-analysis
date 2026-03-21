import pytest

from scraper.database_operations import check_if_car


# ── Real car sale listings (should PASS the filter) ──

@pytest.mark.parametrize("heading", [
    "Mazda 3 2.0i e-SKYACTIV G-122 PLUSTOP benzín manuál 90 kw",
    "Škoda Octavia 1.6 TDI 85kW",
    "BMW 320d xDrive, r.v. 2018, 140kW",
    "Ford Transit Custom 2.0 TDCi",          # dodávka — should pass
    "Mercedes Sprinter 316 CDI",              # dodávka — should pass
    "Volkswagen Crafter 2.0 TDI",             # dodávka — should pass
    "MAN TGE 3.140",                          # nákladní — should pass
    "Iveco Daily 35S14",                       # nákladní — should pass
    "Renault Master 2.3 dCi",                 # dodávka — should pass
    "Peugeot 308 1.5 BlueHDi, nové v ČR",
    "Hyundai Tucson 1.6 T-GDI 4x4",
    "Toyota Yaris 1.5 Hybrid",
    "Audi A4 Avant 2.0 TDI quattro",
])
def test_real_car_passes(heading):
    assert check_if_car("popis auta", heading, price=150000) is True


# ── Parts and accessories (should FAIL) ──

@pytest.mark.parametrize("heading", [
    "Díly Mazda 323F BG",
    "Kola +gumy + hagusy",
    "Kompletní sada kol Mazda 5 R15",
    "Mazda 6, r.v. 2005 - náhradní díly",
    "Prodám nárazník přední Škoda Octavia",
    "Střešní nosič na Fabii",
    "Zimní pneu 205/55 R16",
    "Světla zadní Audi A4",
    "Na díly - Renault Megane",
    "Autodíly VW Golf",
    "Na rozborku Peugeot 307",
])
def test_parts_filtered_out(heading):
    assert check_if_car("popis", heading, price=50000) is False


# ── Buying/searching intent (should FAIL) ──

@pytest.mark.parametrize("heading", [
    "Koupím Škoda Octavia do 200 000 Kč",
    "Hledám Ford Focus kombi",
    "Sháním Volkswagen Passat B8",
    "Poptávám SUV do 300 000",
    "Pronajímám Škoda Superb",
    "Pronájem dodávky Brno",
    "Půjčovna aut Praha",
])
def test_buying_intent_filtered_out(heading):
    assert check_if_car("popis", heading, price=200000) is False


# ── Non-car vehicles (should FAIL) ──

@pytest.mark.parametrize("heading", [
    "Motocykl Honda CBR 600",
    "Motorka Yamaha MT-07",
    "Skútr Honda PCX 125",
    "Moped Piaggio",
    "Autobus Iveco Crossway",
    # New: traktory, karavany, přívěsy
    "Traktor Zetor 7045",
    "Traktor John Deere 6130R",
    "Karavan Hobby De Luxe 495",
    "Karavan Fendt Bianco 465",
    "Obytný vůz Fiat Ducato",
    "Obytný přívěs Dethleffs",
    "Přívěs brzděný 750kg",
    "Přívěsný vozík za auto",
    "Obytňák Adria Matrix",
    "Čtyřkolka Can-Am Outlander",
    "Čtyřkolka Yamaha Grizzly",
    "Tříkolka Piaggio MP3",
    "Golfový vozík Club Car",
    "Rolba Kässbohrer",
    "Vysokozdvižný vozík Linde",
    "Bagr CAT 320",
    "Nakladač Bobcat S650",
])
def test_non_car_vehicles_filtered_out(heading):
    assert check_if_car("popis", heading, price=100000) is False


# ── Price filter (should FAIL) ──

@pytest.mark.parametrize("price", [None, 0, 1000, 4999])
def test_low_price_filtered_out(price):
    assert check_if_car("popis", "Škoda Octavia 1.6 TDI", price=price) is False


# ── Missing heading (should FAIL) ──

def test_empty_heading_filtered_out():
    assert check_if_car("popis", "", price=150000) is False
    assert check_if_car("popis", None, price=150000) is False


# ── Upper price sanity (should FAIL) ──

def test_absurd_price_filtered_out():
    assert check_if_car("popis", "Škoda Fabia 1.2", price=999_999_999) is False
