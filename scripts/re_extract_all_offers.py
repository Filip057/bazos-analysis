#!/usr/bin/env python3
"""
Re-extract data from all offers using improved extraction patterns

This script:
1. Fetches all offers from the database
2. Re-extracts data using improved patterns
3. Updates the database with new extraction results
4. Shows before/after comparison
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
from ml.production_extractor import ProductionExtractor
import time

config = get_config()

def re_extract_all():
    """Re-extract all offers with improved patterns"""

    # Connect to database
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("RE-EXTRACTING ALL OFFERS WITH IMPROVED PATTERNS")
    print("=" * 70)

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM offers")
    total_offers = cursor.fetchone()[0]
    print(f"\nTotal offers to re-extract: {total_offers}")

    # Fetch all offers
    print("\n📥 Fetching offers from database...")
    cursor.execute("""
        SELECT id, title, description, url
        FROM offers
    """)
    offers = cursor.fetchall()

    # Statistics
    stats = {
        'total': 0,
        'year_improved': 0,
        'mileage_improved': 0,
        'power_improved': 0,
        'fuel_improved': 0,
        'errors': 0
    }

    # Initialize extractor
    print("🔧 Initializing improved extractor...")
    extractor = ProductionExtractor()

    print(f"\n🚀 Starting re-extraction...\n")
    start_time = time.time()

    for idx, (offer_id, title, description, url) in enumerate(offers, 1):
        try:
            # Get current values
            cursor.execute("""
                SELECT year_manufacture, mileage, power, fuel
                FROM offers
                WHERE id = %s
            """, (offer_id,))
            current = cursor.fetchone()
            old_year, old_mileage, old_power, old_fuel = current

            # Re-extract
            full_text = f"{title}\n{description}" if description else title
            result = extractor.extract(full_text, car_id=str(offer_id))

            # Extract new values
            new_year = result['year']
            new_mileage = result['mileage']
            new_power = result['power']
            new_fuel = result['fuel']

            # Update database
            cursor.execute("""
                UPDATE offers
                SET year_manufacture = %s,
                    mileage = %s,
                    power = %s,
                    fuel = %s
                WHERE id = %s
            """, (new_year, new_mileage, new_power, new_fuel, offer_id))

            # Track improvements
            stats['total'] += 1
            if old_year is None and new_year is not None:
                stats['year_improved'] += 1
            if old_mileage is None and new_mileage is not None:
                stats['mileage_improved'] += 1
            if old_power is None and new_power is not None:
                stats['power_improved'] += 1
            if old_fuel is None and new_fuel is not None:
                stats['fuel_improved'] += 1

            # Progress indicator
            if idx % 50 == 0:
                elapsed = time.time() - start_time
                rate = idx / elapsed
                remaining = (total_offers - idx) / rate
                print(f"  [{idx}/{total_offers}] "
                      f"Rate: {rate:.1f} offers/sec, "
                      f"ETA: {remaining:.0f}s")

        except Exception as e:
            print(f"  ❌ Error processing offer {offer_id}: {e}")
            stats['errors'] += 1
            continue

    # Commit changes
    conn.commit()

    elapsed = time.time() - start_time

    print(f"\n{'='*70}")
    print("RE-EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"  Total processed:     {stats['total']}")
    print(f"  Year improved:       {stats['year_improved']} (NEW extractions)")
    print(f"  Mileage improved:    {stats['mileage_improved']} (NEW extractions)")
    print(f"  Power improved:      {stats['power_improved']} (NEW extractions)")
    print(f"  Fuel improved:       {stats['fuel_improved']} (NEW extractions)")
    print(f"  Errors:              {stats['errors']}")
    print(f"  Time taken:          {elapsed:.1f}s ({stats['total']/elapsed:.1f} offers/sec)")
    print(f"{'='*70}\n")

    # Show new completeness
    print("📊 NEW COMPLETENESS METRICS:\n")

    for field in ['year_manufacture', 'mileage', 'power', 'fuel']:
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM offers
            WHERE {field} IS NOT NULL
        """)
        non_null = cursor.fetchone()[0]
        completeness = (non_null / total_offers) * 100

        status = "✅" if completeness >= 80 else "⚠️" if completeness >= 70 else "❌"
        print(f"  {status} {field:20s}: {non_null:4d}/{total_offers} ({completeness:5.1f}%)")

    cursor.close()
    conn.close()

    print(f"\n{'='*70}")
    print("NEXT STEP: Run data quality audit to verify improvements")
    print("  python3 scripts/data_quality_audit.py")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    re_extract_all()
