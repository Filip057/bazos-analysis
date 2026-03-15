#!/usr/bin/env python3
"""
Analyze extraction gaps - Find what's in the text but extraction missed

Takes analysis_results.csv and for each failed extraction:
1. Uses AGGRESSIVE regex to find year/mileage/fuel in raw text
2. Compares with what extraction found
3. Reports MISSING patterns

This helps identify what regex patterns we need to add!
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import re

def aggressive_find_year(text):
    """Find ALL possible years in text (aggressive search)"""
    # Find all 4-digit years (1990-2026)
    years = []
    for match in re.finditer(r'\b(19\d{2}|20[0-2]\d)\b', text):
        year = int(match.group(1))
        if 1990 <= year <= 2026:
            years.append({
                'value': year,
                'context': text[max(0, match.start()-30):match.end()+30],
                'position': match.start()
            })
    return years

def aggressive_find_mileage(text):
    """Find ALL possible mileage values in text (aggressive search)"""
    mileages = []

    # Pattern 1: Numbers with km (150000 km, 150 000 km, 150.000 km)
    for match in re.finditer(r'(\d{1,3}(?:[\s._,]\d{3})+|\d{4,6})\s?km', text, re.IGNORECASE):
        value_str = match.group(1).replace(' ', '').replace('.', '').replace('_', '').replace(',', '')
        try:
            value = int(value_str)
            if 1000 <= value <= 999999:  # Reasonable mileage range
                mileages.append({
                    'value': value,
                    'context': text[max(0, match.start()-30):match.end()+30],
                    'position': match.start()
                })
        except:
            pass

    # Pattern 2: "najeto", "nájezd" with numbers
    for match in re.finditer(r'(?:najeto|nájezd)[:\s]+(\d{1,3}(?:[\s._,]\d{3})+|\d{4,6})', text, re.IGNORECASE):
        value_str = match.group(1).replace(' ', '').replace('.', '').replace('_', '').replace(',', '')
        try:
            value = int(value_str)
            if 1000 <= value <= 999999:
                mileages.append({
                    'value': value,
                    'context': text[max(0, match.start()-30):match.end()+30],
                    'position': match.start()
                })
        except:
            pass

    # Pattern 3: Thousands abbreviations (150tis, 150k, 150t)
    for match in re.finditer(r'(\d{1,3})\s?(?:tis|tisíc|k|t)(?:\s?km)?', text, re.IGNORECASE):
        try:
            value = int(match.group(1)) * 1000
            if 1000 <= value <= 999999:
                mileages.append({
                    'value': value,
                    'context': text[max(0, match.start()-30):match.end()+30],
                    'position': match.start()
                })
        except:
            pass

    return mileages

def aggressive_find_fuel(text):
    """Find ALL possible fuel types in text (aggressive search)"""
    fuels = []

    fuel_patterns = [
        r'\b(benzin(?:ový|ového|ovým|ové|ovém)?|benzín(?:ový|ového|ovým|ové|ovém)?)\b',
        r'\b(nafta|naftový(?:ho|mu|m|ém)?|diesel(?:ový|ového|ovým|ové)?)\b',
        r'\b(lpg|cng|plyn)\b',
        r'\b(hybrid|elektro|electric)\b'
    ]

    for pattern in fuel_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            fuels.append({
                'value': match.group(1),
                'context': text[max(0, match.start()-30):match.end()+30],
                'position': match.start()
            })

    return fuels

def analyze_gaps(input_csv, output_csv='gap_analysis.csv'):
    """Analyze what extraction missed"""

    print("=" * 70)
    print("EXTRACTION GAP ANALYSIS")
    print("=" * 70)

    # Read analysis results
    print(f"\n📥 Reading {input_csv}...")

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        results = list(reader)

    print(f"Found {len(results)} offers to analyze\n")

    # Analyze gaps
    gaps = []
    stats = {
        'total': 0,
        'year_gaps': 0,
        'mileage_gaps': 0,
        'fuel_gaps': 0,
        'no_gaps': 0
    }

    for row in results:
        offer_id = row['id']
        full_text = f"{row['scraped_title']}\n{row['scraped_description']}"

        extracted_year = int(row['extracted_year']) if row['extracted_year'] and row['extracted_year'] != 'None' else None
        extracted_mileage = int(row['extracted_mileage']) if row['extracted_mileage'] and row['extracted_mileage'] != 'None' else None
        extracted_fuel = row['extracted_fuel'] if row['extracted_fuel'] != 'None' else None

        # Find what's in the text (aggressive)
        found_years = aggressive_find_year(full_text)
        found_mileages = aggressive_find_mileage(full_text)
        found_fuels = aggressive_find_fuel(full_text)

        # Check for gaps
        year_gap = None
        if extracted_year is None and found_years:
            year_gap = found_years[0]  # Take first match
            stats['year_gaps'] += 1

        mileage_gap = None
        if extracted_mileage is None and found_mileages:
            mileage_gap = found_mileages[0]
            stats['mileage_gaps'] += 1

        fuel_gap = None
        if extracted_fuel is None and found_fuels:
            fuel_gap = found_fuels[0]
            stats['fuel_gaps'] += 1

        # Record gap
        if year_gap or mileage_gap or fuel_gap:
            gaps.append({
                'id': offer_id,
                'url': row['url'],
                'gap_type': ','.join(filter(None, [
                    'year' if year_gap else None,
                    'mileage' if mileage_gap else None,
                    'fuel' if fuel_gap else None
                ])),
                'missed_year': year_gap['value'] if year_gap else None,
                'missed_year_context': year_gap['context'] if year_gap else None,
                'missed_mileage': mileage_gap['value'] if mileage_gap else None,
                'missed_mileage_context': mileage_gap['context'] if mileage_gap else None,
                'missed_fuel': fuel_gap['value'] if fuel_gap else None,
                'missed_fuel_context': fuel_gap['context'] if fuel_gap else None,
                'extracted_year': extracted_year,
                'extracted_mileage': extracted_mileage,
                'extracted_fuel': extracted_fuel
            })
        else:
            stats['no_gaps'] += 1

        stats['total'] += 1

    # Write gaps to CSV
    print(f"💾 Writing gap analysis to {output_csv}...")

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'id', 'url', 'gap_type',
            'missed_year', 'missed_year_context',
            'missed_mileage', 'missed_mileage_context',
            'missed_fuel', 'missed_fuel_context',
            'extracted_year', 'extracted_mileage', 'extracted_fuel'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(gaps)

    # Statistics
    print(f"\n{'='*70}")
    print("GAP ANALYSIS RESULTS")
    print(f"{'='*70}")
    print(f"  Total analyzed:        {stats['total']}")
    print(f"  Year gaps found:       {stats['year_gaps']} (text HAS year, extraction MISSED)")
    print(f"  Mileage gaps found:    {stats['mileage_gaps']} (text HAS mileage, extraction MISSED)")
    print(f"  Fuel gaps found:       {stats['fuel_gaps']} (text HAS fuel, extraction MISSED)")
    print(f"  No gaps (truly empty): {stats['no_gaps']}")
    print(f"{'='*70}\n")

    print(f"✅ Gap analysis saved to: {output_csv}")
    print(f"\nNEXT STEP:")
    print(f"  1. Open {output_csv} and review 'missed_*_context' columns")
    print(f"  2. Identify PATTERNS that extraction is missing")
    print(f"  3. Add these patterns to ml/context_aware_patterns.py")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze extraction gaps')
    parser.add_argument('input_csv', help='Input CSV file (from scrape_and_analyze_incomplete.py)')
    parser.add_argument('--output', type=str, default='gap_analysis.csv', help='Output CSV file')

    args = parser.parse_args()

    analyze_gaps(args.input_csv, args.output)
