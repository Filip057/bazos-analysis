#!/usr/bin/env python3
"""Quick DB check - simple sync version"""

import pymysql

def check_db():
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='bazos_user',
        password='bazos_password555',
        db='bazos_cars'
    )

    cursor = conn.cursor()

    # Count brands
    cursor.execute("SELECT COUNT(*) FROM brands")
    brands_count = cursor.fetchone()[0]

    # Count models
    cursor.execute("SELECT COUNT(*) FROM models")
    models_count = cursor.fetchone()[0]

    # Count offers
    cursor.execute("SELECT COUNT(*) FROM offers")
    offers_count = cursor.fetchone()[0]

    print(f"📊 Databáze:")
    print(f"  Brands:  {brands_count:,}")
    print(f"  Models:  {models_count:,}")
    print(f"  Offers:  {offers_count:,}")

    # Show sample brands if any
    if brands_count > 0:
        print("\n🏷️  Značky (prvních 10):")
        cursor.execute("SELECT name FROM brands LIMIT 10")
        for row in cursor.fetchall():
            print(f"  - {row[0]}")

    if models_count > 0:
        print("\n🚗 Modely (prvních 10):")
        cursor.execute("SELECT m.name, b.name FROM models m JOIN brands b ON m.brand_id = b.id LIMIT 10")
        for model, brand in cursor.fetchall():
            print(f"  - {brand} {model}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_db()
