#!/usr/bin/env python3
"""
Auto-Labeling Export: Export offers with AUTO-EXTRACTED labels for verification

This script:
1. Exports random sample of offers from DB
2. Scrapes fresh title + description
3. AUTO-EXTRACTS data using IMPROVED patterns (context_aware_patterns.py)
4. Creates CSV for FAST verification (just check if correct, don't type!)

Usage:
    python3 scripts/export_for_auto_labeling.py --count 500

Output CSV columns:
    id, url, text, auto_year, auto_mileage, auto_fuel, auto_power,
    verified_year, verified_mileage, verified_fuel, verified_power, correct

Workflow:
    1. Run this script → creates auto_labeled_sample.csv
    2. Open CSV in Excel/LibreOffice
    3. For each row:
       - Check if auto_* values are CORRECT
       - If YES: set correct=1
       - If NO: fix values in verified_* columns, set correct=0
    4. Save CSV
    5. Run import_verified_labels.py → creates training data
    6. Re-train ML model
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
from ml.production_extractor import ProductionExtractor
import csv
import requests
from bs4 import BeautifulSoup
import random

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

        # Extract title
        title_elem = soup.find('h1', class_='nadpisdetail')
        title = title_elem.get_text(strip=True) if title_elem else ''

        # Extract description
        desc_elem = soup.find('div', class_='popisdetail')
        description = desc_elem.get_text(strip=True) if desc_elem else ''

        return title, description

    except Exception as e:
        return None, None

def export_auto_labeled(sample_size=500, output_file='auto_labeled_sample.csv'):
    """Export random offers with auto-extracted labels"""

    print("=" * 70)
    print("AUTO-LABELING EXPORT (for fast verification)")
    print("=" * 70)

    # Connect to database
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    # Get random sample
    print(f"\n📥 Fetching random sample of {sample_size} offers...")
    cursor.execute("""
        SELECT id, url
        FROM offers
        WHERE url IS NOT NULL
        ORDER BY RAND()
        LIMIT %s
    """, (sample_size,))
    offers = cursor.fetchall()
    print(f"Found {len(offers)} offers")

    # Initialize extractor (IMPROVED patterns!)
    print("🔧 Initializing IMPROVED extractor...")
    extractor = ProductionExtractor()

    # Process each offer
    print(f"\n🚀 Scraping + auto-extracting {len(offers)} offers...")
    print("   (This will take ~3-5 minutes)\n")

    results = []
    failed = 0

    for idx, (offer_id, url) in enumerate(offers, 1):
        # Progress
        if idx % 50 == 0:
            print(f"  [{idx}/{len(offers)}] processed...")

        # Scrape
        title, description = scrape_offer(url)

        if title is None:
            failed += 1
            continue

        # Auto-extract using IMPROVED patterns
        full_text = f"{title}\n{description}" if description else title
        extraction = extractor.extract(full_text, car_id=str(offer_id))

        # Store result
        results.append({
            'id': offer_id,
            'url': url,
            'text': full_text[:500] + '...' if len(full_text) > 500 else full_text,  # Truncate for CSV
            'auto_year': extraction['year'] or '',
            'auto_mileage': extraction['mileage'] or '',
            'auto_fuel': extraction['fuel'] or '',
            'auto_power': extraction['power'] or '',
            'verified_year': '',  # User fills this if auto is wrong
            'verified_mileage': '',
            'verified_fuel': '',
            'verified_power': '',
            'correct': ''  # User marks 1=correct, 0=incorrect
        })

    # Write CSV
    print(f"\n💾 Writing to {output_file}...")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'id', 'url', 'text',
            'auto_year', 'auto_mileage', 'auto_fuel', 'auto_power',
            'verified_year', 'verified_mileage', 'verified_fuel', 'verified_power',
            'correct'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    cursor.close()
    conn.close()

    # Summary
    print(f"\n{'='*70}")
    print("EXPORT COMPLETE")
    print(f"{'='*70}")
    print(f"  Total offers:        {len(offers)}")
    print(f"  Successfully scraped: {len(results)}")
    print(f"  Failed scrapes:      {failed}")
    print(f"\n  Output file:         {output_file}")
    print(f"{'='*70}\n")

    print("NEXT STEPS:")
    print("  1. Open auto_labeled_sample.csv in Excel/LibreOffice")
    print("  2. For each row:")
    print("     - Check if auto_* values are CORRECT")
    print("     - If YES: set 'correct' column = 1")
    print("     - If NO: fix values in 'verified_*' columns, set 'correct' = 0")
    print("  3. Save CSV")
    print("  4. Run: python3 scripts/import_verified_labels.py")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Export offers with auto-extracted labels for verification')
    parser.add_argument('--count', type=int, default=500, help='Number of offers to export (default: 500)')
    parser.add_argument('--output', type=str, default='auto_labeled_sample.csv', help='Output CSV file')

    args = parser.parse_args()

    export_auto_labeled(sample_size=args.count, output_file=args.output)
