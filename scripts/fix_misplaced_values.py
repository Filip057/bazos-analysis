#!/usr/bin/env python3
"""
Fix misplaced values (e.g., mileage in fuel field)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import re
from webapp.config import get_config

config = get_config()

def extract_mileage_from_text(text):
    """Extract mileage from text like '111tkm', '150 000 km', etc."""
    if not text:
        return None

    # Pattern: digits + optional spaces + km/tkm
    match = re.search(r'(\d+(?:\s?\d+)*)\s*t?km', text.lower())
    if match:
        # Remove spaces and convert to int
        mileage_str = match.group(1).replace(' ', '')
        mileage = int(mileage_str)

        # Handle "tkm" (thousands of km)
        if 'tkm' in text.lower():
            mileage *= 1000

        return mileage

    return None

def fix_misplaced():
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("FIX MISPLACED VALUES")
    print("=" * 70)

    # Find fuel fields containing mileage-like values
    cursor.execute("""
        SELECT id, fuel, mileage
        FROM offers
        WHERE fuel REGEXP '[0-9]'
    """)

    misplaced = cursor.fetchall()

    if not misplaced:
        print("\n✅ No misplaced values found!")
        cursor.close()
        conn.close()
        return

    print(f"\nFound {len(misplaced)} offers with numbers in fuel field:")

    fixed = 0
    for offer_id, fuel_value, current_mileage in misplaced[:10]:  # Show first 10
        extracted_mileage = extract_mileage_from_text(fuel_value)

        if extracted_mileage:
            print(f"\n  ID {offer_id}:")
            print(f"    fuel: '{fuel_value}' → extracted: {extracted_mileage:,} km")
            print(f"    current mileage: {current_mileage}")

    # Ask for confirmation
    print("\n" + "=" * 70)
    response = input("Do you want to fix these values? (y/n): ")

    if response.lower() != 'y':
        print("Cancelled.")
        cursor.close()
        conn.close()
        return

    # Fix values
    for offer_id, fuel_value, current_mileage in misplaced:
        extracted_mileage = extract_mileage_from_text(fuel_value)

        if extracted_mileage:
            # Update mileage if missing
            if current_mileage is None:
                cursor.execute("""
                    UPDATE offers
                    SET mileage = %s, fuel = NULL
                    WHERE id = %s
                """, (extracted_mileage, offer_id))
                fixed += 1
            else:
                # Just clear fuel field if mileage already exists
                cursor.execute("""
                    UPDATE offers
                    SET fuel = NULL
                    WHERE id = %s
                """, (offer_id,))
                fixed += 1

    conn.commit()
    print(f"\n✓ Fixed {fixed} records")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    fix_misplaced()
