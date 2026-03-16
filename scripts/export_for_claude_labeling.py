#!/usr/bin/env python3
"""
Export Offers for Claude Labeling

Simplest workflow:
1. Export random sample → JSON with id, url, text
2. Send JSON to Claude chat
3. Claude extracts year/mileage/fuel/power → returns spaCy training format
4. Use directly for ML training

NO auto-extraction, NO verification steps - just scraping!

Usage:
    python3 scripts/export_for_claude_labeling.py --count 500

Output:
    offers_for_labeling.json
    [
      {
        "id": 1,
        "url": "https://...",
        "text": "full text (heading + description)"
      },
      ...
    ]

Then:
    - Upload offers_for_labeling.json to Claude chat
    - Ask Claude to extract entities → spaCy format
    - Claude returns training_data.json
    - Use for ML training!
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from webapp.config import get_config
import json
import requests
from bs4 import BeautifulSoup
import time

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
        print(f"  ⚠️  Failed to scrape {url}: {e}")
        return None, None

def export_for_claude(sample_size=500, output_file='offers_for_labeling.json'):
    """Export random offers for Claude to label"""

    print("=" * 70)
    print("EXPORT FOR CLAUDE LABELING")
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

    # Scrape each offer
    print(f"\n🚀 Scraping {len(offers)} offers...")
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

        # Combine title + description
        full_text = f"{title}\n{description}" if description else title

        # Store result
        results.append({
            'id': offer_id,
            'url': url,
            'text': full_text
        })

        # Rate limiting (be nice to Bazos.cz)
        time.sleep(0.1)

    # Write JSON
    print(f"\n💾 Writing to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

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
    print(f"  File size:           {os.path.getsize(output_file) / 1024:.1f} KB")
    print(f"{'='*70}\n")

    print("NEXT STEPS:")
    print("  1. Upload offers_for_labeling.json to Claude chat")
    print("  2. Use this prompt:")
    print()
    print('     """')
    print('     Extrahuj z těchto nabídek rok výroby, nájezd km, palivo a výkon.')
    print('     Vrať spaCy training formát s entity positions.')
    print('     ')
    print('     ENTITY TYPES:')
    print('     - YEAR: rok výroby (YYYY)')
    print('     - MILEAGE: nájezd (km číslo)')
    print('     - FUEL: palivo (benzín/diesel/lpg/elektro/hybrid)')
    print('     - POWER: výkon (kW číslo)')
    print('     ')
    print('     OUTPUT FORMAT:')
    print('     [')
    print('       ["text", {"entities": [[start, end, "TYPE"], ...]}],')
    print('       ...')
    print('     ]')
    print('     """')
    print()
    print("  3. Claude returns training_data.json")
    print("  4. Use for ML training:")
    print("     python3 ml/train_model.py --input training_data.json")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Export offers for Claude to label')
    parser.add_argument('--count', type=int, default=500, help='Number of offers to export (default: 500)')
    parser.add_argument('--output', type=str, default='offers_for_labeling.json', help='Output JSON file')

    args = parser.parse_args()

    export_for_claude(sample_size=args.count, output_file=args.output)
