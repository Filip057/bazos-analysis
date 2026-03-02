#!/usr/bin/env python3
"""
Debug database to find where data went
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from webapp.config import get_config

config = get_config()
engine = create_engine(config.DATABASE_URI)

print("=" * 80)
print("DATABASE DEBUG")
print("=" * 80)
print(f"Database URI: {config.DATABASE_URI.replace(config.MYSQL_PASSWORD, '***')}")
print()

with engine.connect() as conn:
    # 1. List all tables
    print("1. TABLES IN DATABASE:")
    print("-" * 80)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    print()

    # 2. Count rows in each table
    print("2. ROW COUNTS:")
    print("-" * 80)
    for table in tables:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"  {table:<30} {count:>10,} rows")
        except Exception as e:
            print(f"  {table:<30} ERROR: {e}")
    print()

    # 3. Check brands table
    if 'brands' in tables:
        print("3. BRANDS TABLE:")
        print("-" * 80)
        result = conn.execute(text("SELECT id, name FROM brands"))
        for row in result:
            print(f"  ID {row[0]}: {row[1]}")
        print()

    # 4. Check models table
    if 'models' in tables:
        print("4. MODELS TABLE (sample):")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT m.id, b.name as brand, m.name as model
            FROM models m
            JOIN brands b ON m.brand_id = b.id
            LIMIT 10
        """))
        for row in result:
            print(f"  ID {row[0]}: {row[1]} {row[2]}")
        print()

    # 5. Check offers table structure
    if 'offers' in tables:
        print("5. OFFERS TABLE STRUCTURE:")
        print("-" * 80)
        result = conn.execute(text("DESCRIBE offers"))
        for row in result:
            print(f"  {row[0]:<30} {row[1]:<20} {row[2]:<5} {row[3]:<5}")
        print()

    # 6. Check if car_view exists (old structure)
    if 'car_view' in tables:
        print("6. CAR_VIEW TABLE (old structure):")
        print("-" * 80)
        result = conn.execute(text("SELECT COUNT(*) FROM car_view"))
        count = result.fetchone()[0]
        print(f"  car_view has {count:,} rows")
        print()

print("=" * 80)
print("DIAGNOSIS:")
print("=" * 80)
print("If offers table is empty but pipeline reported 11,786 saved:")
print("1. Check if pipeline is using --skip-db flag")
print("2. Check if there's a different database being used")
print("3. Check pipeline logs for actual DB write errors")
print("4. Verify database/model.py is using correct engine")
print("=" * 80)
