#!/usr/bin/env python3
"""
Add derived columns to offers table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config

config = get_config()

def migrate():
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    try:
        print("Checking for missing columns...")

        # Check if columns exist
        cursor.execute("DESCRIBE offers")
        columns = [row[0] for row in cursor.fetchall()]

        missing = []
        if 'years_in_usage' not in columns:
            missing.append('years_in_usage')
        if 'price_per_km' not in columns:
            missing.append('price_per_km')
        if 'mileage_per_year' not in columns:
            missing.append('mileage_per_year')

        if not missing:
            print("✓ All columns already exist!")
            return

        print(f"Adding missing columns: {', '.join(missing)}")

        # Add missing columns
        if 'years_in_usage' in missing:
            cursor.execute("ALTER TABLE offers ADD COLUMN years_in_usage INT NULL")
            print("  ✓ Added years_in_usage")

        if 'price_per_km' in missing:
            cursor.execute("ALTER TABLE offers ADD COLUMN price_per_km FLOAT NULL")
            print("  ✓ Added price_per_km")

        if 'mileage_per_year' in missing:
            cursor.execute("ALTER TABLE offers ADD COLUMN mileage_per_year FLOAT NULL")
            print("  ✓ Added mileage_per_year")

        conn.commit()
        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"✗ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
