#!/usr/bin/env python3
"""
Scrape FRESH data from incomplete offers and run improved extraction

Input: CSV with incomplete offers (from export_incomplete_offers.py)
Output: CSV with scraped data + extraction results for analysis

Output columns:
  - id, url
  - scraped_title, scraped_description
  - extracted_year, extracted_mileage, extracted_fuel, extracted_power
  - current_year, current_mileage, current_fuel, current_power
  - extraction_improved (YES/NO)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import requests
from bs4 import BeautifulSoup
import time
from ml.production_extractor import ProductionExtractor

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
        print(f"  ❌ Error scraping {url}: {e}")
        return None, None

def analyze_incomplete_offers(input_csv, output_csv='analysis_results.csv'):
    """Scrape and analyze incomplete offers"""

    print("=" * 70)
    print("SCRAPING & ANALYZING INCOMPLETE OFFERS")
    print("=" * 70)

    # Initialize extractor
    print("\n🔧 Initializing improved extractor...")
    extractor = ProductionExtractor()

    # Read input CSV
    print(f"📥 Reading {input_csv}...")

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        offers = list(reader)

    print(f"Found {len(offers)} offers to analyze\n")

    # Process each offer
    results = []
    stats = {
        'total': 0,
        'scraped': 0,
        'failed_scrape': 0,
        'year_improved': 0,
        'mileage_improved': 0,
        'fuel_improved': 0,
        'power_improved': 0
    }

    print("🚀 Starting scraping + extraction...\n")

    for idx, offer in enumerate(offers, 1):
        offer_id = offer['id']
        url = offer['url']

        print(f"[{idx}/{len(offers)}] Processing ID {offer_id}...")

        # Scrape fresh data
        title, description = scrape_offer(url)

        if title is None:
            stats['failed_scrape'] += 1
            results.append({
                'id': offer_id,
                'url': url,
                'scraped_title': 'SCRAPE_FAILED',
                'scraped_description': 'SCRAPE_FAILED',
                'extracted_year': None,
                'extracted_mileage': None,
                'extracted_fuel': None,
                'extracted_power': None,
                'current_year': offer['current_year'],
                'current_mileage': offer['current_mileage'],
                'current_fuel': offer['current_fuel'],
                'current_power': offer['current_power'],
                'extraction_improved': 'SCRAPE_FAILED'
            })
            continue

        stats['scraped'] += 1

        # Extract data using IMPROVED patterns
        full_text = f"{title}\n{description}"
        extraction = extractor.extract(full_text, car_id=offer_id)

        # Compare with current DB values
        current_year = int(offer['current_year']) if offer['current_year'] and offer['current_year'] != 'None' else None
        current_mileage = int(offer['current_mileage']) if offer['current_mileage'] and offer['current_mileage'] != 'None' else None
        current_fuel = offer['current_fuel'] if offer['current_fuel'] != 'None' else None
        current_power = int(offer['current_power']) if offer['current_power'] and offer['current_power'] != 'None' else None

        extracted_year = extraction['year']
        extracted_mileage = extraction['mileage']
        extracted_fuel = extraction['fuel']
        extracted_power = extraction['power']

        # Check if extraction improved
        improved = []
        if current_year is None and extracted_year is not None:
            improved.append('year')
            stats['year_improved'] += 1
        if current_mileage is None and extracted_mileage is not None:
            improved.append('mileage')
            stats['mileage_improved'] += 1
        if current_fuel is None and extracted_fuel is not None:
            improved.append('fuel')
            stats['fuel_improved'] += 1
        if current_power is None and extracted_power is not None:
            improved.append('power')
            stats['power_improved'] += 1

        extraction_improved = ','.join(improved) if improved else 'NO'

        results.append({
            'id': offer_id,
            'url': url,
            'scraped_title': title,
            'scraped_description': description[:500] + '...' if len(description) > 500 else description,  # Truncate for CSV
            'extracted_year': extracted_year,
            'extracted_mileage': extracted_mileage,
            'extracted_fuel': extracted_fuel,
            'extracted_power': extracted_power,
            'current_year': current_year,
            'current_mileage': current_mileage,
            'current_fuel': current_fuel,
            'current_power': current_power,
            'extraction_improved': extraction_improved
        })

        stats['total'] += 1

        # Rate limiting (be nice to Bazos)
        time.sleep(0.5)

    # Write results to CSV
    print(f"\n💾 Writing results to {output_csv}...")

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'id', 'url',
            'scraped_title', 'scraped_description',
            'extracted_year', 'extracted_mileage', 'extracted_fuel', 'extracted_power',
            'current_year', 'current_mileage', 'current_fuel', 'current_power',
            'extraction_improved'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Print statistics
    print(f"\n{'='*70}")
    print("ANALYSIS RESULTS")
    print(f"{'='*70}")
    print(f"  Total processed:     {stats['total']}")
    print(f"  Successfully scraped: {stats['scraped']}")
    print(f"  Failed scrapes:      {stats['failed_scrape']}")
    print(f"\n  IMPROVEMENTS:")
    print(f"    Year improved:     {stats['year_improved']}")
    print(f"    Mileage improved:  {stats['mileage_improved']}")
    print(f"    Fuel improved:     {stats['fuel_improved']}")
    print(f"    Power improved:    {stats['power_improved']}")
    print(f"{'='*70}\n")

    print(f"✅ Results saved to: {output_csv}")
    print(f"\nNEXT STEP:")
    print(f"  1. Open {output_csv} in Excel/LibreOffice")
    print(f"  2. Filter for extraction_improved='NO' (still failing)")
    print(f"  3. Manually check scraped_title + scraped_description")
    print(f"  4. Identify patterns that are MISSING from extraction")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Scrape and analyze incomplete offers')
    parser.add_argument('input_csv', help='Input CSV file (from export_incomplete_offers.py)')
    parser.add_argument('--output', type=str, default='analysis_results.csv', help='Output CSV file')

    args = parser.parse_args()

    analyze_incomplete_offers(args.input_csv, args.output)
