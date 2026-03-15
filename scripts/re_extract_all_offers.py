#!/usr/bin/env python3
"""
Re-extract data from all offers using improved extraction patterns

This script:
1. Fetches all offers (URLs) from the database
2. SCRAPES fresh title + description from each URL
3. Re-extracts data using improved patterns
4. Updates the database with new extraction results
5. Shows before/after comparison

NOTE: This script SCRAPES fresh data because title/description are NOT stored in DB.
      For 1049 offers, expect ~10-15 minutes runtime.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
from ml.production_extractor import ProductionExtractor
import time
import requests
from bs4 import BeautifulSoup

config = get_config()

def scrape_offer(url):
    """Scrape title and description from Bazos offer URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title (headline)
        title_elem = soup.find('h1', class_='nadpisdetail')
        title = title_elem.get_text(strip=True) if title_elem else ''

        # Extract description
        desc_elem = soup.find('div', class_='popisdetail')
        description = desc_elem.get_text(strip=True) if desc_elem else ''

        return title, description

    except Exception as e:
        return None, None

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

    # Fetch all offers (URL only, will scrape fresh data)
    print("\n📥 Fetching offer URLs from database...")
    cursor.execute("""
        SELECT id, url
        FROM offers
        WHERE url IS NOT NULL
    """)
    offers = cursor.fetchall()
    print(f"Found {len(offers)} offers with URLs")

    # Statistics
    stats = {
        'total': 0,
        'year_improved': 0,
        'mileage_improved': 0,
        'power_improved': 0,
        'fuel_improved': 0,
        'year_kept': 0,        # Existing value kept (prevented regression)
        'mileage_kept': 0,
        'power_kept': 0,
        'fuel_kept': 0,
        'scrape_failed': 0,    # Failed to scrape URL
        'errors': 0
    }

    # Initialize extractor
    print("🔧 Initializing improved extractor...")
    extractor = ProductionExtractor()

    print(f"\n🚀 Starting scraping + re-extraction...")
    print(f"   (Scraping {len(offers)} URLs, ETA: ~{len(offers)*0.5/60:.0f} minutes)\n")
    start_time = time.time()

    for idx, (offer_id, url) in enumerate(offers, 1):
        try:
            # Get current values
            cursor.execute("""
                SELECT year_manufacture, mileage, power, fuel
                FROM offers
                WHERE id = %s
            """, (offer_id,))
            current = cursor.fetchone()
            old_year, old_mileage, old_power, old_fuel = current

            # Scrape fresh data
            title, description = scrape_offer(url)

            if title is None:
                stats['scrape_failed'] += 1
                stats['total'] += 1
                continue

            # Re-extract
            full_text = f"{title}\n{description}" if description else title
            result = extractor.extract(full_text, car_id=str(offer_id))

            # Rate limiting (be nice to Bazos)
            time.sleep(0.3)  # 300ms between requests

            # Extract new values
            new_year = result['year']
            new_mileage = result['mileage']
            new_power = result['power']
            new_fuel = result['fuel']

            # CRITICAL FIX: Keep existing values if new extraction returns None
            # (prevents regression where good data is replaced with NULL)
            final_year = new_year if new_year is not None else old_year
            final_mileage = new_mileage if new_mileage is not None else old_mileage
            final_power = new_power if new_power is not None else old_power
            final_fuel = new_fuel if new_fuel is not None else old_fuel

            # Update database (only update if new value is better)
            cursor.execute("""
                UPDATE offers
                SET year_manufacture = %s,
                    mileage = %s,
                    power = %s,
                    fuel = %s
                WHERE id = %s
            """, (final_year, final_mileage, final_power, final_fuel, offer_id))

            # Track improvements (only count NEW extractions, not kept values)
            stats['total'] += 1
            if old_year is None and new_year is not None:
                stats['year_improved'] += 1
            if old_mileage is None and new_mileage is not None:
                stats['mileage_improved'] += 1
            if old_power is None and new_power is not None:
                stats['power_improved'] += 1
            if old_fuel is None and new_fuel is not None:
                stats['fuel_improved'] += 1

            # Track kept values (regression prevention)
            if old_year is not None and new_year is None:
                stats['year_kept'] += 1
            if old_mileage is not None and new_mileage is None:
                stats['mileage_kept'] += 1
            if old_power is not None and new_power is None:
                stats['power_kept'] += 1
            if old_fuel is not None and new_fuel is None:
                stats['fuel_kept'] += 1

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
    print(f"  Scrape failed:       {stats['scrape_failed']} (URL not accessible)")
    print(f"\n  IMPROVEMENTS (NULL → value):")
    print(f"    Year improved:       {stats['year_improved']}")
    print(f"    Mileage improved:    {stats['mileage_improved']}")
    print(f"    Power improved:      {stats['power_improved']}")
    print(f"    Fuel improved:       {stats['fuel_improved']}")
    print(f"\n  REGRESSION PREVENTION (kept existing values):")
    print(f"    Year kept:           {stats['year_kept']} (extraction failed, kept old value)")
    print(f"    Mileage kept:        {stats['mileage_kept']}")
    print(f"    Power kept:          {stats['power_kept']}")
    print(f"    Fuel kept:           {stats['fuel_kept']}")
    print(f"\n  Errors:              {stats['errors']}")
    print(f"  Time taken:          {elapsed:.1f}s ({elapsed/60:.1f} min, {stats['total']/elapsed:.1f} offers/sec)")
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
