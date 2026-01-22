"""
Normalize Extracted Data for Database
======================================

This script normalizes raw extracted car data before database insertion.

Normalization includes:
- Fuel types: "benzínový" → "benzín", "dieselový" → "diesel"
- Power units: Extract numbers only, remove "kW/KW/kw"
- Mileage: Remove separators (dots, spaces), extract numbers only
- Year: Ensure 4-digit format

Usage:
    # Normalize single record
    python3 -m ml.normalize_for_db --text "Motor dieselový 145 KW"

    # Normalize JSON file
    python3 -m ml.normalize_for_db --file extraction_results.json

    # Normalize review queue
    python3 -m ml.normalize_for_db --review-queue
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

from ml.data_normalizer import DataNormalizer


def normalize_extraction(raw_data: Dict) -> Dict:
    """
    Normalize raw extraction data for database storage.

    Args:
        raw_data: Dictionary with raw extracted values
                 {'mileage': '187.000 km', 'year': 2015, 'power': '145 KW', 'fuel': 'dieselový'}

    Returns:
        Normalized dictionary ready for database
        {'mileage': 187000, 'year': 2015, 'power': 145, 'fuel': 'diesel'}
    """
    normalizer = DataNormalizer()

    normalized = {}

    # Normalize each field
    if 'mileage' in raw_data:
        normalized['mileage'] = normalizer.normalize_mileage(raw_data['mileage'])

    if 'year' in raw_data:
        normalized['year'] = normalizer.normalize_year(raw_data['year'])

    if 'power' in raw_data:
        normalized['power'] = normalizer.normalize_power(raw_data['power'])

    if 'fuel' in raw_data:
        normalized['fuel'] = normalizer.normalize_fuel(raw_data['fuel'])

    return normalized


def normalize_file(file_path: Path, output_path: Optional[Path] = None):
    """
    Normalize all extractions in a JSON file.

    Args:
        file_path: Path to JSON file with raw extractions
        output_path: Optional output path (defaults to *_normalized.json)
    """
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    # Load data
    print(f"📂 Loading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Determine structure
    if isinstance(data, list):
        # List of extractions
        records = data
    elif isinstance(data, dict) and 'extractions' in data:
        # Structured format
        records = data['extractions']
    else:
        print(f"❌ Unknown format in {file_path}")
        return

    # Normalize each record
    print(f"🔄 Normalizing {len(records)} records...")
    normalized_records = []

    for i, record in enumerate(records):
        try:
            # Extract raw values
            if 'raw_values' in record:
                raw = record['raw_values']
            elif all(k in record for k in ['mileage', 'year', 'power', 'fuel']):
                raw = record
            else:
                print(f"  ⚠️  Skipping record {i+1}: No extractable data")
                continue

            # Normalize
            normalized = normalize_extraction(raw)

            # Keep metadata
            normalized_record = {
                **record,  # Keep original metadata
                **normalized,  # Overwrite with normalized values
                '_normalization_applied': True
            }

            normalized_records.append(normalized_record)

        except Exception as e:
            print(f"  ❌ Error normalizing record {i+1}: {e}")

    # Determine output path
    if output_path is None:
        output_path = file_path.with_name(f"{file_path.stem}_normalized.json")

    # Save normalized data
    print(f"💾 Saving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(normalized_records, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Normalized {len(normalized_records)} records")
    print(f"   Output: {output_path}")


def normalize_review_queue(queue_file: str = 'review_queue.json',
                           output_file: Optional[str] = None):
    """
    Normalize extractions in review queue.

    Shows both RAW and NORMALIZED values side by side for comparison.
    """
    queue_path = Path(queue_file)

    if not queue_path.exists():
        print(f"❌ Review queue not found: {queue_file}")
        return

    # Load queue
    print(f"📂 Loading {queue_file}...")
    with open(queue_path, 'r', encoding='utf-8') as f:
        queue = json.load(f)

    print(f"   Found {len(queue)} items in queue")

    # Normalize each item
    print(f"\n{'='*60}")
    print(f"Normalization Preview (first 5 items)")
    print(f"{'='*60}")

    normalized_queue = []

    for i, item in enumerate(queue):
        # Get raw results
        ml_raw = item.get('ml_result', {})
        regex_raw = item.get('regex_result', {})

        # Normalize both
        ml_normalized = normalize_extraction(ml_raw)
        regex_normalized = normalize_extraction(regex_raw)

        # Add to normalized queue
        normalized_item = {
            **item,
            'ml_result_normalized': ml_normalized,
            'regex_result_normalized': regex_normalized
        }
        normalized_queue.append(normalized_item)

        # Show preview for first 5
        if i < 5:
            print(f"\nItem {i+1}: {item.get('car_id', 'Unknown')[:50]}...")
            print(f"  ML RAW:        {ml_raw}")
            print(f"  ML NORMALIZED: {ml_normalized}")
            print(f"  Regex RAW:        {regex_raw}")
            print(f"  Regex NORMALIZED: {regex_normalized}")

    if len(queue) > 5:
        print(f"\n  ... and {len(queue) - 5} more")

    # Save
    if output_file is None:
        output_file = 'review_queue_normalized.json'

    print(f"\n💾 Saving normalized queue to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(normalized_queue, f, ensure_ascii=False, indent=2)

    print(f"✅ Done! Normalized {len(normalized_queue)} items")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize raw extraction data for database storage"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--text',
        help='Normalize a single text extract (JSON format)'
    )
    group.add_argument(
        '--file',
        help='Normalize extractions from a JSON file'
    )
    group.add_argument(
        '--review-queue',
        action='store_true',
        help='Normalize review_queue.json'
    )

    parser.add_argument(
        '--output',
        help='Output file path (optional)'
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🧹 Data Normalization for Database")
    print(f"{'='*60}\n")

    if args.text:
        # Parse and normalize single extraction
        try:
            raw_data = json.loads(args.text)
            normalized = normalize_extraction(raw_data)

            print("RAW input:")
            print(json.dumps(raw_data, indent=2, ensure_ascii=False))
            print("\nNORMALIZED output:")
            print(json.dumps(normalized, indent=2, ensure_ascii=False))

        except json.JSONDecodeError:
            print("❌ Invalid JSON format")

    elif args.file:
        # Normalize file
        file_path = Path(args.file)
        output_path = Path(args.output) if args.output else None
        normalize_file(file_path, output_path)

    elif args.review_queue:
        # Normalize review queue
        normalize_review_queue(output_file=args.output)

    print(f"\n{'='*60}")
    print(f"✓ Normalization complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
