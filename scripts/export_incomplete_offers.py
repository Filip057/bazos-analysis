#!/usr/bin/env python3
"""
Export incomplete offers (missing year OR mileage) to CSV for analysis

Output CSV columns:
  - id, url, current_year, current_mileage, current_fuel, current_power
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
import csv

config = get_config()

def export_incomplete_offers(limit=100, output_file='incomplete_offers.csv'):
    """Export incomplete offers to CSV"""

    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("EXPORTING INCOMPLETE OFFERS")
    print("=" * 70)

    # Get incomplete offers (missing year OR mileage)
    print(f"\n📥 Fetching {limit} incomplete offers...")

    cursor.execute("""
        SELECT id, url, year_manufacture, mileage, fuel, power
        FROM offers
        WHERE year_manufacture IS NULL OR mileage IS NULL
        ORDER BY id
        LIMIT %s
    """, (limit,))

    offers = cursor.fetchall()

    print(f"Found {len(offers)} incomplete offers\n")

    # Write to CSV
    print(f"💾 Writing to {output_file}...")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'id', 'url',
            'current_year', 'current_mileage', 'current_fuel', 'current_power'
        ])

        # Data
        for row in offers:
            writer.writerow(row)

    cursor.close()
    conn.close()

    print(f"✅ Exported {len(offers)} offers to {output_file}")
    print(f"\n{'='*70}")
    print("NEXT STEP:")
    print(f"  python3 scripts/scrape_and_analyze_incomplete.py {output_file}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Export incomplete offers to CSV')
    parser.add_argument('--limit', type=int, default=100, help='Number of offers to export (default: 100)')
    parser.add_argument('--output', type=str, default='incomplete_offers.csv', help='Output CSV file')

    args = parser.parse_args()

    export_incomplete_offers(limit=args.limit, output_file=args.output)
