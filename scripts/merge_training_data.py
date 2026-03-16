#!/usr/bin/env python3
"""
Merge Training Data - Combine old + new training data

Incremental training strategy:
1. Start with existing training data
2. Add new Claude-labeled samples
3. Deduplicate (avoid training on same offer twice)
4. Train improved model

Usage:
    # Merge new data into existing
    python3 scripts/merge_training_data.py \
        --existing training_data_labeled.json \
        --new training_data_new.json \
        --output training_data_combined.json

    # Merge multiple sources
    python3 scripts/merge_training_data.py \
        --existing training_data_labeled.json filtered_training_skoda.json \
        --new training_data_new.json \
        --output training_data_combined.json
"""
import json
import argparse
from typing import List, Dict, Set
from pathlib import Path


def load_training_data(file_path: str) -> List:
    """Load training data from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_to_spacy_format(data: List) -> List:
    """
    Normalize different training data formats to spaCy format

    Supports:
    - spaCy format: [["text", {"entities": [...]}], ...]
    - Dict format: [{"text": "...", "entities": [...], ...}, ...]
    """
    normalized = []

    for item in data:
        # Already in spaCy format: ["text", {"entities": [...]}]
        if isinstance(item, list) and len(item) == 2:
            normalized.append(item)

        # Dict format: {"text": "...", "entities": [...]}
        elif isinstance(item, dict):
            text = item.get('text', '')
            entities = item.get('entities', [])

            # If entities is list of tuples/lists, convert to dict format
            if isinstance(entities, list) and len(entities) > 0:
                if isinstance(entities[0], (list, tuple)):
                    # Entities are already position tuples: [[start, end, "TYPE"], ...]
                    normalized.append([text, {"entities": entities}])
                else:
                    # Entities might be in different format
                    normalized.append([text, {"entities": []}])
            else:
                normalized.append([text, {"entities": entities if isinstance(entities, list) else []}])

        else:
            print(f"⚠️  Unknown format: {type(item)}")

    return normalized


def deduplicate_training_data(data: List) -> List:
    """
    Remove duplicate training examples based on text
    Keep first occurrence
    """
    seen_texts: Set[str] = set()
    deduplicated = []
    duplicates = 0

    for item in data:
        text = item[0] if isinstance(item, list) else item.get('text', '')

        # Use first 100 chars as dedup key (full text might have minor variations)
        text_key = text[:100].strip()

        if text_key not in seen_texts:
            seen_texts.add(text_key)
            deduplicated.append(item)
        else:
            duplicates += 1

    if duplicates > 0:
        print(f"  Removed {duplicates} duplicates")

    return deduplicated


def analyze_training_data(data: List) -> Dict:
    """Analyze training data statistics"""
    stats = {
        'total_samples': len(data),
        'entity_counts': {
            'YEAR': 0,
            'MILEAGE': 0,
            'FUEL': 0,
            'POWER': 0
        },
        'samples_with_entities': 0,
        'empty_samples': 0
    }

    for item in data:
        entities = item[1].get('entities', []) if isinstance(item, list) else item.get('entities', [])

        if len(entities) > 0:
            stats['samples_with_entities'] += 1
            for entity in entities:
                entity_type = entity[2] if len(entity) > 2 else None
                if entity_type in stats['entity_counts']:
                    stats['entity_counts'][entity_type] += 1
        else:
            stats['empty_samples'] += 1

    return stats


def merge_training_data(existing_files: List[str], new_file: str, output_file: str):
    """Merge existing + new training data with deduplication"""

    print("=" * 70)
    print("MERGE TRAINING DATA")
    print("=" * 70)

    all_data = []

    # Load existing data
    print(f"\n📥 Loading EXISTING training data...")
    for file_path in existing_files:
        if not Path(file_path).exists():
            print(f"  ⚠️  File not found: {file_path}")
            continue

        data = load_training_data(file_path)
        normalized = normalize_to_spacy_format(data)
        all_data.extend(normalized)
        print(f"  ✅ {file_path}: {len(normalized)} samples")

    print(f"\n  Total existing: {len(all_data)} samples")

    # Load new data
    print(f"\n📥 Loading NEW training data...")
    if Path(new_file).exists():
        new_data = load_training_data(new_file)
        normalized_new = normalize_to_spacy_format(new_data)
        all_data.extend(normalized_new)
        print(f"  ✅ {new_file}: {len(normalized_new)} samples")
    else:
        print(f"  ⚠️  File not found: {new_file}")
        normalized_new = []

    # Deduplicate
    print(f"\n🔍 Deduplicating...")
    print(f"  Before: {len(all_data)} samples")
    deduplicated = deduplicate_training_data(all_data)
    print(f"  After:  {len(deduplicated)} samples")

    # Analyze
    print(f"\n📊 Analyzing combined data...")
    stats = analyze_training_data(deduplicated)

    print(f"\n  Total samples:       {stats['total_samples']}")
    print(f"  With entities:       {stats['samples_with_entities']} ({stats['samples_with_entities']/stats['total_samples']*100:.1f}%)")
    print(f"  Empty (no entities): {stats['empty_samples']} ({stats['empty_samples']/stats['total_samples']*100:.1f}%)")
    print(f"\n  Entity counts:")
    for entity_type, count in stats['entity_counts'].items():
        print(f"    {entity_type:10s}: {count}")

    # Save
    print(f"\n💾 Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(deduplicated, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n{'='*70}")
    print("MERGE COMPLETE")
    print(f"{'='*70}")
    print(f"  Existing samples:  {len(all_data) - len(normalized_new)}")
    print(f"  New samples:       {len(normalized_new)}")
    print(f"  Combined (dedup):  {len(deduplicated)}")
    print(f"\n  Output file:       {output_file}")
    print(f"{'='*70}\n")

    print("NEXT STEP:")
    print(f"  python3 ml/train_model.py --input {output_file}")
    print(f"\n{'='*70}\n")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Merge training data files')
    parser.add_argument('--existing', nargs='+', required=True, help='Existing training data file(s)')
    parser.add_argument('--new', required=True, help='New training data file')
    parser.add_argument('--output', default='training_data_combined.json', help='Output file')

    args = parser.parse_args()

    merge_training_data(args.existing, args.new, args.output)
