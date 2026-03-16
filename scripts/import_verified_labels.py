#!/usr/bin/env python3
"""
Import Verified Labels: Convert verified CSV to ML training data

Reads auto_labeled_sample.csv (after user verification) and creates:
1. training_data.json (spaCy format)
2. Statistics about verification results

Usage:
    python3 scripts/import_verified_labels.py --input auto_labeled_sample.csv
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import json
from typing import List, Dict

def convert_to_spacy_format(verified_data: List[Dict]) -> List[Dict]:
    """Convert verified labels to spaCy training format"""
    training_data = []

    for item in verified_data:
        text = item['text']

        # Use verified_* if provided, otherwise use auto_*
        year = item['verified_year'] if item['verified_year'] else item['auto_year']
        mileage = item['verified_mileage'] if item['verified_mileage'] else item['auto_mileage']
        fuel = item['verified_fuel'] if item['verified_fuel'] else item['auto_fuel']
        power = item['verified_power'] if item['verified_power'] else item['auto_power']

        # Create entities list with character positions
        entities = []

        # Find entity positions in text
        if year and str(year) in text:
            start = text.find(str(year))
            end = start + len(str(year))
            entities.append((start, end, 'YEAR'))

        if mileage and str(mileage) in text:
            start = text.find(str(mileage))
            end = start + len(str(mileage))
            entities.append((start, end, 'MILEAGE'))

        if fuel and str(fuel).lower() in text.lower():
            start = text.lower().find(str(fuel).lower())
            end = start + len(str(fuel))
            entities.append((start, end, 'FUEL'))

        if power and str(power) in text:
            start = text.find(str(power))
            end = start + len(str(power))
            entities.append((start, end, 'POWER'))

        # Add to training data
        training_data.append({
            'text': text,
            'entities': entities,
            'metadata': {
                'id': item['id'],
                'url': item['url'],
                'year': year,
                'mileage': mileage,
                'fuel': fuel,
                'power': power,
                'auto_correct': item['correct'] == '1'
            }
        })

    return training_data

def import_verified_labels(input_file='auto_labeled_sample.csv', output_file='training_data_verified.json'):
    """Import verified labels and convert to training data"""

    print("=" * 70)
    print("IMPORT VERIFIED LABELS")
    print("=" * 70)

    # Read CSV
    print(f"\n📥 Reading {input_file}...")

    verified_data = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        verified_data = list(reader)

    print(f"Found {len(verified_data)} verified samples")

    # Statistics
    stats = {
        'total': len(verified_data),
        'auto_correct': 0,
        'manually_corrected': 0,
        'empty': 0
    }

    for item in verified_data:
        if item['correct'] == '1':
            stats['auto_correct'] += 1
        elif item['correct'] == '0':
            stats['manually_corrected'] += 1
        else:
            stats['empty'] += 1

    # Convert to spaCy format
    print("\n🔧 Converting to spaCy training format...")
    training_data = convert_to_spacy_format(verified_data)

    # Write output
    print(f"💾 Writing to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n{'='*70}")
    print("IMPORT COMPLETE")
    print(f"{'='*70}")
    print(f"  Total samples:           {stats['total']}")
    print(f"  Auto-correct (no changes): {stats['auto_correct']} ({stats['auto_correct']/stats['total']*100:.1f}%)")
    print(f"  Manually corrected:      {stats['manually_corrected']} ({stats['manually_corrected']/stats['total']*100:.1f}%)")
    print(f"  Not verified (empty):    {stats['empty']}")
    print(f"\n  Output file:             {output_file}")
    print(f"{'='*70}\n")

    print("NEXT STEP:")
    print("  python3 ml/train_model.py --input training_data_verified.json")
    print(f"\n{'='*70}\n")

    # Show auto-extraction accuracy
    if stats['auto_correct'] + stats['manually_corrected'] > 0:
        accuracy = stats['auto_correct'] / (stats['auto_correct'] + stats['manually_corrected']) * 100
        print(f"📊 AUTO-EXTRACTION ACCURACY: {accuracy:.1f}%")
        print(f"   (Using IMPROVED patterns from context_aware_patterns.py)")
        print()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Import verified labels and create training data')
    parser.add_argument('--input', type=str, default='auto_labeled_sample.csv', help='Input CSV file')
    parser.add_argument('--output', type=str, default='training_data_verified.json', help='Output JSON file')

    args = parser.parse_args()

    import_verified_labels(input_file=args.input, output_file=args.output)
