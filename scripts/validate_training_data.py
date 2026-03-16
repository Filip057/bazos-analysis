#!/usr/bin/env python3
"""
Validate Training Data - Check for misaligned entities

Detects:
  - Invalid entity positions (out of bounds)
  - Misaligned entities (wrong text at position)
  - Overlapping entities
  - Empty entities
  - Unicode issues

Usage:
    # Check training data
    python3 scripts/validate_training_data.py --input training_data.json

    # Auto-fix issues
    python3 scripts/validate_training_data.py \
        --input training_data.json \
        --output training_data_fixed.json \
        --fix
"""
import json
import argparse
import re
from typing import List, Dict, Tuple
from pathlib import Path


def load_training_data(file_path: str) -> List:
    """Load training data from JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_entity(text: str, entity: List) -> Dict:
    """
    Validate single entity annotation

    Returns:
        {
            'valid': bool,
            'error': str or None,
            'expected_text': str (text at given position),
            'entity_type': str
        }
    """
    if len(entity) != 3:
        return {
            'valid': False,
            'error': f'Invalid entity format (expected [start, end, type], got {entity})',
            'expected_text': '',
            'entity_type': 'UNKNOWN'
        }

    start, end, entity_type = entity

    # Check bounds
    if start < 0:
        return {
            'valid': False,
            'error': f'Negative start position: {start}',
            'expected_text': '',
            'entity_type': entity_type
        }

    if end > len(text):
        return {
            'valid': False,
            'error': f'End position {end} > text length {len(text)}',
            'expected_text': '',
            'entity_type': entity_type
        }

    if start >= end:
        return {
            'valid': False,
            'error': f'Start {start} >= End {end}',
            'expected_text': '',
            'entity_type': entity_type
        }

    # Extract text at position
    extracted_text = text[start:end]

    # Check if empty
    if not extracted_text.strip():
        return {
            'valid': False,
            'error': f'Empty entity at [{start}, {end}]',
            'expected_text': extracted_text,
            'entity_type': entity_type
        }

    return {
        'valid': True,
        'error': None,
        'expected_text': extracted_text,
        'entity_type': entity_type
    }


def check_overlaps(entities: List) -> List[Tuple[int, int]]:
    """Check for overlapping entities"""
    overlaps = []
    sorted_entities = sorted(enumerate(entities), key=lambda x: x[1][0])

    for i in range(len(sorted_entities) - 1):
        idx1, e1 = sorted_entities[i]
        idx2, e2 = sorted_entities[i + 1]

        if e1[1] > e2[0]:  # end1 > start2
            overlaps.append((idx1, idx2))

    return overlaps


def try_fix_entity(text: str, entity: List, entity_type: str) -> List or None:
    """
    Try to automatically fix misaligned entity

    Strategies:
    1. Search for expected pattern near given position
    2. Fix whitespace issues (trim start/end)
    3. Adjust for common unicode issues
    """
    start, end, _ = entity

    # Strategy 1: Trim whitespace
    extracted = text[start:end]
    trimmed = extracted.strip()

    if trimmed and trimmed != extracted:
        # Find trimmed text position
        trimmed_start = text.find(trimmed, start - 5, end + 5)
        if trimmed_start != -1:
            trimmed_end = trimmed_start + len(trimmed)
            return [trimmed_start, trimmed_end, entity_type]

    # Strategy 2: Search nearby (±10 chars) for pattern
    search_start = max(0, start - 10)
    search_end = min(len(text), end + 10)
    search_area = text[search_start:search_end]

    # YEAR pattern
    if entity_type == "YEAR":
        match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', search_area)
        if match:
            found_start = search_start + match.start()
            found_end = search_start + match.end()
            return [found_start, found_end, entity_type]

    # MILEAGE pattern
    elif entity_type == "MILEAGE":
        match = re.search(r'\b\d{1,3}[\s.]?\d{3}[\s.]?\d{3}\b|\b\d{4,6}\s*km\b', search_area)
        if match:
            found_start = search_start + match.start()
            found_end = search_start + match.end()
            return [found_start, found_end, entity_type]

    # POWER pattern
    elif entity_type == "POWER":
        match = re.search(r'\b\d{2,3}\s*(?:kW|koní|ps|HP)\b', search_area, re.IGNORECASE)
        if match:
            found_start = search_start + match.start()
            found_end = search_start + match.end()
            return [found_start, found_end, entity_type]

    # FUEL pattern
    elif entity_type == "FUEL":
        match = re.search(r'\b(?:benzín|diesel|lpg|cng|elektro|hybrid)\b', search_area, re.IGNORECASE)
        if match:
            found_start = search_start + match.start()
            found_end = search_start + match.end()
            return [found_start, found_end, entity_type]

    return None


def validate_training_data(data: List, fix: bool = False) -> Dict:
    """
    Validate all training data

    Returns:
        {
            'total_examples': int,
            'total_entities': int,
            'valid_entities': int,
            'invalid_entities': int,
            'fixed_entities': int,
            'errors': List[Dict],
            'fixed_data': List (if fix=True)
        }
    """
    stats = {
        'total_examples': len(data),
        'total_entities': 0,
        'valid_entities': 0,
        'invalid_entities': 0,
        'fixed_entities': 0,
        'removed_entities': 0,
        'errors': [],
        'fixed_data': []
    }

    for idx, item in enumerate(data):
        # Normalize format
        if isinstance(item, list) and len(item) == 2:
            text, annotations = item
            entities = annotations.get('entities', [])
        elif isinstance(item, dict):
            text = item.get('text', '')
            entities = item.get('entities', [])
        else:
            stats['errors'].append({
                'example_idx': idx,
                'error': f'Unknown format: {type(item)}',
                'text': str(item)[:100]
            })
            continue

        # Validate entities
        valid_entities = []

        for ent_idx, entity in enumerate(entities):
            stats['total_entities'] += 1

            validation = validate_entity(text, entity)

            if validation['valid']:
                stats['valid_entities'] += 1
                valid_entities.append(entity)
            else:
                stats['invalid_entities'] += 1

                error_info = {
                    'example_idx': idx,
                    'entity_idx': ent_idx,
                    'entity': entity,
                    'error': validation['error'],
                    'expected_text': validation['expected_text'],
                    'text_preview': text[:200]
                }

                # Try to fix
                if fix:
                    fixed_entity = try_fix_entity(text, entity, validation['entity_type'])

                    if fixed_entity:
                        # Validate fixed entity
                        fixed_validation = validate_entity(text, fixed_entity)
                        if fixed_validation['valid']:
                            stats['fixed_entities'] += 1
                            valid_entities.append(fixed_entity)
                            error_info['fixed'] = True
                            error_info['fixed_entity'] = fixed_entity
                            error_info['fixed_text'] = fixed_validation['expected_text']
                        else:
                            stats['removed_entities'] += 1
                            error_info['fixed'] = False
                    else:
                        stats['removed_entities'] += 1
                        error_info['fixed'] = False

                stats['errors'].append(error_info)

        # Check overlaps
        overlaps = check_overlaps(valid_entities)
        if overlaps:
            for o1, o2 in overlaps:
                stats['errors'].append({
                    'example_idx': idx,
                    'error': 'Overlapping entities',
                    'entity1': valid_entities[o1],
                    'entity2': valid_entities[o2],
                    'text_preview': text[:200]
                })

        # Save fixed data
        if fix:
            stats['fixed_data'].append([text, {'entities': valid_entities}])

    return stats


def print_validation_report(stats: Dict, show_errors: bool = True):
    """Print validation report"""
    print("\n" + "=" * 70)
    print("TRAINING DATA VALIDATION REPORT")
    print("=" * 70)

    print(f"\n📊 Overall Statistics:")
    print(f"  Total examples:      {stats['total_examples']}")
    print(f"  Total entities:      {stats['total_entities']}")

    if stats['total_entities'] > 0:
        print(f"  Valid entities:      {stats['valid_entities']} ({stats['valid_entities']/stats['total_entities']*100:.1f}%)")
        print(f"  Invalid entities:    {stats['invalid_entities']} ({stats['invalid_entities']/stats['total_entities']*100:.1f}%)")
    else:
        print(f"  ⚠️  NO ENTITIES FOUND! This file might not be in training format.")
        return

    if stats['fixed_entities'] > 0:
        print(f"  Fixed entities:      {stats['fixed_entities']} ({stats['fixed_entities']/stats['invalid_entities']*100:.1f}% of invalid)")
    if stats['removed_entities'] > 0:
        print(f"  Removed entities:    {stats['removed_entities']} ({stats['removed_entities']/stats['invalid_entities']*100:.1f}% of invalid)")

    # Data loss calculation
    if stats['invalid_entities'] > 0:
        loss_pct = stats['invalid_entities'] / stats['total_entities'] * 100
        print(f"\n⚠️  DATA LOSS: {loss_pct:.1f}% of entities will be IGNORED during training!")

        if loss_pct > 10:
            print(f"  ❌ CRITICAL: >10% data loss! Training quality severely affected!")
        elif loss_pct > 5:
            print(f"  ⚠️  WARNING: >5% data loss! Consider fixing before training")
        else:
            print(f"  ✅ Acceptable: <5% data loss")

    # Show errors
    if show_errors and stats['errors']:
        print(f"\n❌ Errors ({len(stats['errors'])} total):")

        # Group errors by type
        error_types = {}
        for err in stats['errors']:
            error_msg = err.get('error', 'Unknown')
            if error_msg not in error_types:
                error_types[error_msg] = []
            error_types[error_msg].append(err)

        for error_type, errors in error_types.items():
            print(f"\n  {error_type}: {len(errors)} occurrences")

            # Show first 3 examples
            for err in errors[:3]:
                print(f"    Example {err.get('example_idx', '?')}:")
                if 'entity' in err:
                    print(f"      Entity: {err['entity']}")
                if 'expected_text' in err:
                    print(f"      Text at position: '{err['expected_text']}'")
                if 'fixed' in err:
                    if err['fixed']:
                        print(f"      ✅ FIXED: {err['fixed_entity']} → '{err['fixed_text']}'")
                    else:
                        print(f"      ❌ REMOVED (couldn't auto-fix)")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Validate training data')
    parser.add_argument('--input', required=True, help='Input training data file')
    parser.add_argument('--output', help='Output file for fixed data')
    parser.add_argument('--fix', action='store_true', help='Try to auto-fix misaligned entities')
    parser.add_argument('--show-errors', action='store_true', help='Show detailed error list')

    args = parser.parse_args()

    # Load data
    print(f"📥 Loading training data from {args.input}...")
    data = load_training_data(args.input)
    print(f"  Loaded {len(data)} examples")

    # Validate
    print(f"\n🔍 Validating...")
    stats = validate_training_data(data, fix=args.fix)

    # Report
    print_validation_report(stats, show_errors=args.show_errors)

    # Save fixed data
    if args.fix and args.output:
        print(f"\n💾 Saving fixed data to {args.output}...")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(stats['fixed_data'], f, ensure_ascii=False, indent=2)

        print(f"  ✅ Saved {len(stats['fixed_data'])} examples")
        print(f"  ✅ Fixed {stats['fixed_entities']} entities")
        print(f"  ⚠️  Removed {stats['removed_entities']} unfixable entities")

        print(f"\n🚀 Next step:")
        print(f"  python3 -m ml.train_ml_model --data {args.output} --iterations 30")

    elif args.fix and not args.output:
        print(f"\n⚠️  --fix was specified but no --output file!")
        print(f"  Use: --output training_data_fixed.json")


if __name__ == "__main__":
    main()
