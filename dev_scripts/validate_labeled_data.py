#!/usr/bin/env python3
"""
Validate GPT-Labeled Data
--------------------------
Checks if GPT output is in correct spaCy training format.

Usage:
    python3 validate_labeled_data.py auto_labeled_193.json

Checks:
  - Valid JSON
  - Correct spaCy format: [[text, {entities: [...]}], ...]
  - Entity positions match text
  - No normalization (e.g., "193.500" not changed to "193500")
  - Entity labels are valid (YEAR, MILEAGE, FUEL, POWER)
"""

import json
import sys
import argparse
from pathlib import Path

VALID_LABELS = {'YEAR', 'MILEAGE', 'FUEL', 'POWER'}

def validate_file(file_path, verbose=False):
    """Validate labeled data file"""

    print(f"🔍 Validating {file_path}...")
    print("=" * 70)

    # Check file exists
    if not Path(file_path).exists():
        print(f"❌ ERROR: File not found: {file_path}")
        return False

    # Load JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Valid JSON")
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON!")
        print(f"   {e}")
        return False

    # Check is list
    if not isinstance(data, list):
        print(f"❌ ERROR: Data is not a list (got {type(data).__name__})")
        return False

    print(f"✅ Is a list ({len(data)} examples)")

    # Validate each example
    errors = 0
    warnings = 0

    for i, example in enumerate(data):
        # Check format: [text, {entities: [...]}]
        if not isinstance(example, list) or len(example) != 2:
            print(f"❌ Example {i}: Not [text, annotations] format")
            errors += 1
            continue

        text, annotations = example

        # Check text is string
        if not isinstance(text, str):
            print(f"❌ Example {i}: Text is not a string")
            errors += 1
            continue

        # Check annotations is dict with 'entities'
        if not isinstance(annotations, dict):
            print(f"❌ Example {i}: Annotations is not a dict")
            errors += 1
            continue

        if 'entities' not in annotations:
            print(f"❌ Example {i}: Missing 'entities' key")
            errors += 1
            continue

        entities = annotations['entities']

        # Check entities is list
        if not isinstance(entities, list):
            print(f"❌ Example {i}: Entities is not a list")
            errors += 1
            continue

        # Validate each entity
        for j, entity in enumerate(entities):
            # Check format: [start, end, label]
            if not isinstance(entity, list) or len(entity) != 3:
                print(f"❌ Example {i}, Entity {j}: Not [start, end, label] format")
                errors += 1
                continue

            start, end, label = entity

            # Check positions are integers
            if not isinstance(start, int) or not isinstance(end, int):
                print(f"❌ Example {i}, Entity {j}: Positions not integers ({type(start).__name__}, {type(end).__name__})")
                errors += 1
                continue

            # Check label is string
            if not isinstance(label, str):
                print(f"❌ Example {i}, Entity {j}: Label not string")
                errors += 1
                continue

            # Check label is valid
            if label not in VALID_LABELS:
                print(f"⚠️  Example {i}, Entity {j}: Unknown label '{label}' (expected one of: {VALID_LABELS})")
                warnings += 1

            # Check positions are valid
            if start < 0 or end > len(text) or start >= end:
                print(f"❌ Example {i}, Entity {j}: Invalid positions [{start}, {end}] for text length {len(text)}")
                errors += 1
                continue

            # Extract entity text
            entity_text = text[start:end]

            # Check for normalization issues (common GPT mistake!)
            if label == 'MILEAGE':
                # Check if entity text contains dots/spaces (good!)
                # vs being normalized (bad!)
                if entity_text.isdigit() and len(entity_text) >= 5:
                    # Might be normalized (e.g., "193500" instead of "193.500")
                    # Check if original text around this position has dots
                    context_start = max(0, start - 10)
                    context_end = min(len(text), end + 10)
                    context = text[context_start:context_end]

                    if '.' in context or ' tis' in context.lower():
                        print(f"⚠️  Example {i}, Entity {j}: Possible normalization issue!")
                        print(f"     Entity: '{entity_text}' (no formatting)")
                        print(f"     Context: '{context}'")
                        print(f"     Expected: Entity should match exact text (with dots/spaces)")
                        warnings += 1

            if verbose and (i < 3 or (errors > 0 and i == errors)):
                # Show sample entities
                print(f"   Example {i}, Entity {j}: [{start}, {end}, '{label}'] → '{entity_text}'")

    print("=" * 70)
    print(f"📊 Validation Summary:")
    print(f"   Total examples: {len(data)}")
    print(f"   Errors: {errors}")
    print(f"   Warnings: {warnings}")

    if errors == 0 and warnings == 0:
        print(f"\n✅ PERFECT! Data is valid and ready for training!")
        return True
    elif errors == 0:
        print(f"\n⚠️  Data is valid but has {warnings} warnings")
        print(f"   (warnings won't prevent training but may indicate quality issues)")
        return True
    else:
        print(f"\n❌ FAILED! Found {errors} errors that must be fixed!")
        return False

def show_statistics(file_path):
    """Show dataset statistics"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n📊 Dataset Statistics:")
    print("=" * 70)

    # Count examples with entities
    with_entities = sum(1 for ex in data if ex[1]['entities'])
    print(f"Examples with entities: {with_entities}/{len(data)} ({with_entities/len(data)*100:.1f}%)")

    # Count entity types
    entity_counts = {}
    total_entities = 0

    for ex in data:
        for entity in ex[1]['entities']:
            label = entity[2]
            entity_counts[label] = entity_counts.get(label, 0) + 1
            total_entities += 1

    print(f"Total entities: {total_entities}")
    print(f"Avg per example: {total_entities/len(data):.2f}")
    print(f"\nEntity distribution:")
    for label, count in sorted(entity_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/total_entities*100:.1f}%)")

    # Sample examples
    print(f"\n📝 Sample Examples:")
    print("=" * 70)

    import random
    samples = random.sample(data, min(3, len(data)))

    for i, (text, annotations) in enumerate(samples, 1):
        print(f"\nExample {i}:")
        print(f"  Text: {text[:120]}...")
        print(f"  Entities:")
        for start, end, label in annotations['entities']:
            entity_text = text[start:end]
            print(f"    [{start:4d}, {end:4d}, {label:8s}] → \"{entity_text}\"")

def main():
    parser = argparse.ArgumentParser(
        description='Validate GPT-labeled training data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate file
  python3 validate_labeled_data.py auto_labeled_193.json

  # Validate with verbose output
  python3 validate_labeled_data.py auto_labeled_193.json --verbose

  # Show statistics only
  python3 validate_labeled_data.py auto_labeled_193.json --stats-only

Exit codes:
  0 = Valid (ready for training)
  1 = Invalid (has errors)
        """
    )

    parser.add_argument('file', help='Labeled data file to validate')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')
    parser.add_argument('-s', '--stats', action='store_true', help='Show statistics')
    parser.add_argument('--stats-only', action='store_true', help='Only show statistics (skip validation)')

    args = parser.parse_args()

    if args.stats_only:
        show_statistics(args.file)
        return

    # Validate
    is_valid = validate_file(args.file, verbose=args.verbose)

    # Show stats if requested
    if args.stats and is_valid:
        show_statistics(args.file)

    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == '__main__':
    main()
