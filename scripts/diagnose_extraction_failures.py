#!/usr/bin/env python3
"""
Diagnose why extraction is failing for 40-50% of offers
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
import re

config = get_config()

def diagnose():
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=int(config.MYSQL_PORT),
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DATABASE
    )

    cursor = conn.cursor()

    print("=" * 70)
    print("EXTRACTION FAILURE DIAGNOSIS")
    print("=" * 70)

    # Get sample of failed extractions
    print("\n🔍 Fetching offers with missing year/mileage...")

    cursor.execute("""
        SELECT id, url
        FROM offers
        WHERE (year_manufacture IS NULL OR mileage IS NULL)
        LIMIT 10
    """)

    failed_offers = cursor.fetchall()

    if not failed_offers:
        print("✅ No failed extractions found!")
        cursor.close()
        conn.close()
        return

    print(f"\nFound {len(failed_offers)} examples. Checking URLs for patterns...\n")

    # Analyze URLs to understand data availability
    for offer_id, url in failed_offers:
        print(f"ID {offer_id}: {url}")

        # Note: We can't fetch the actual page content here,
        # but we can log the URLs for manual inspection

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Manually check 2-3 URLs above to see if data IS available in the listing
2. If YES → extraction pattern is broken, needs fixing
3. If NO → data genuinely missing from listing (OK)

To improve extraction:
  - Check ml/production_extractor.py patterns
  - Look at auto_training_data.json for successful examples
  - Compare with failed examples
  - Add more robust regex fallbacks
    """)

    # Check extraction confidence distribution
    print("\n" + "=" * 70)
    print("EXTRACTION FILES CHECK")
    print("=" * 70)

    # Check if training data exists
    if os.path.exists('auto_training_data.json'):
        import json
        with open('auto_training_data.json', 'r') as f:
            training_data = json.load(f)
        print(f"  ✓ auto_training_data.json: {len(training_data)} examples")
    else:
        print("  ✗ auto_training_data.json not found")

    if os.path.exists('review_queue.json'):
        import json
        with open('review_queue.json', 'r') as f:
            review_queue = json.load(f)
        print(f"  ⚠️  review_queue.json: {len(review_queue)} items need review")
    else:
        print("  ✓ review_queue.json not found (no disagreements)")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    diagnose()
