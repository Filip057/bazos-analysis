#!/usr/bin/env python3
"""
Normalize fuel types to standard values
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import re
from webapp.config import get_config

config = get_config()

# Normalization rules
FUEL_NORMALIZATION = {
    # benzin variants
    r'benzin.*': 'benzin',
    r'lpg.*': 'lpg',

    # diesel variants
    r'diesel.*': 'diesel',
    r'nafta.*': 'diesel',

    # elektro variants
    r'elektr.*': 'elektro',
    r'electric.*': 'elektro',

    # hybrid variants
    r'hybrid.*': 'hybrid',

    # CNG variants
    r'cng.*': 'cng',
    r'zemní plyn.*': 'cng',
}

def normalize():
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("FUEL TYPE NORMALIZATION")
    print("=" * 70)

    # Get current fuel types
    cursor.execute("SELECT DISTINCT fuel FROM offers WHERE fuel IS NOT NULL")
    current_types = [row[0] for row in cursor.fetchall()]

    print(f"\nCurrent fuel types ({len(current_types)}):")
    for fuel in sorted(current_types):
        print(f"  - {fuel}")

    # Normalize each type
    print("\n" + "=" * 70)
    print("NORMALIZING...")
    print("=" * 70)

    updated = 0
    for pattern, normalized in FUEL_NORMALIZATION.items():
        cursor.execute("""
            UPDATE offers
            SET fuel = %s
            WHERE fuel REGEXP %s AND fuel != %s
        """, (normalized, pattern, normalized))

        count = cursor.rowcount
        if count > 0:
            updated += count
            print(f"  ✓ '{pattern}' → '{normalized}': {count} records")

    conn.commit()

    # Show final state
    print("\n" + "=" * 70)
    print("FINAL STATE")
    print("=" * 70)

    cursor.execute("""
        SELECT fuel, COUNT(*) as count
        FROM offers
        WHERE fuel IS NOT NULL
        GROUP BY fuel
        ORDER BY count DESC
    """)

    final_types = cursor.fetchall()
    print(f"\nFinal fuel types ({len(final_types)}):")
    for fuel, count in final_types:
        print(f"  {fuel:15s}: {count:5d} records")

    print(f"\n✓ Total updated: {updated} records")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    normalize()
