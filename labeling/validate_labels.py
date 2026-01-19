"""
Validate and Fix Labeled Training Data
=======================================

Checks for common labeling errors:
- Overlapping entities (same text labeled as multiple types)
- Misaligned entities (text not found in original)
- Empty entities

Usage:
    python3 validate_labels.py training_data_labeled.json
"""

import json
import sys


def check_overlaps(entities):
    """Check if any entities overlap"""
    overlaps = []
    sorted_entities = sorted(entities, key=lambda x: x[0])

    for i in range(len(sorted_entities) - 1):
        start1, end1, label1 = sorted_entities[i]
        start2, end2, label2 = sorted_entities[i + 1]

        # Check if they overlap
        if start2 < end1:
            overlaps.append({
                'entity1': (start1, end1, label1),
                'entity2': (start2, end2, label2)
            })

    return overlaps


def check_alignment(text, entities):
    """Check if labeled text actually exists in the original text"""
    misaligned = []

    for start, end, label in entities:
        if start < 0 or end > len(text):
            misaligned.append({
                'entity': (start, end, label),
                'reason': 'Out of bounds'
            })
        elif start >= end:
            misaligned.append({
                'entity': (start, end, label),
                'reason': 'Invalid range (start >= end)'
            })

    return misaligned


def validate_labeled_data(file_path):
    """Find all labeling errors"""

    print(f"\n{'='*60}")
    print(f"Validating Labeled Data")
    print(f"{'='*60}")
    print(f"File: {file_path}\n")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_examples = len(data)
    examples_with_errors = 0
    total_overlaps = 0
    total_misaligned = 0

    errors_by_example = []

    for i, item in enumerate(data):
        # Handle both tuple and dict format
        if isinstance(item, (list, tuple)):
            text, annotations = item
            entities = annotations.get('entities', [])
        else:
            text = item.get('text', '')
            entities = item.get('entities', [])

        example_errors = {
            'index': i,
            'text_preview': text[:80] + '...' if len(text) > 80 else text,
            'overlaps': [],
            'misaligned': []
        }

        # Check for overlaps
        overlaps = check_overlaps(entities)
        if overlaps:
            example_errors['overlaps'] = overlaps
            total_overlaps += len(overlaps)

        # Check alignment
        misaligned = check_alignment(text, entities)
        if misaligned:
            example_errors['misaligned'] = misaligned
            total_misaligned += len(misaligned)

        if overlaps or misaligned:
            examples_with_errors += 1
            errors_by_example.append(example_errors)

    # Print summary
    print(f"📊 Validation Summary:")
    print(f"{'='*60}")
    print(f"Total examples:           {total_examples}")
    print(f"Examples with errors:     {examples_with_errors}")
    print(f"Total overlapping labels: {total_overlaps}")
    print(f"Total misaligned labels:  {total_misaligned}")
    print(f"{'='*60}\n")

    if examples_with_errors == 0:
        print(f"✅ All labels are valid! Ready to train.\n")
        return True

    # Show detailed errors
    print(f"❌ Found {examples_with_errors} examples with errors:\n")

    for err in errors_by_example:
        print(f"Example {err['index'] + 1}:")
        print(f"  Text: {err['text_preview']}")

        if err['overlaps']:
            print(f"  ⚠️  OVERLAPPING LABELS:")
            for overlap in err['overlaps']:
                e1_start, e1_end, e1_label = overlap['entity1']
                e2_start, e2_end, e2_label = overlap['entity2']

                # Get the actual text from the data
                if isinstance(data[err['index']], (list, tuple)):
                    text, _ = data[err['index']]
                else:
                    text = data[err['index']].get('text', '')

                text1 = text[e1_start:e1_end]
                text2 = text[e2_start:e2_end]

                print(f"     - {e1_label}: '{text1}' at ({e1_start}, {e1_end})")
                print(f"     - {e2_label}: '{text2}' at ({e2_start}, {e2_end})")

        if err['misaligned']:
            print(f"  ⚠️  MISALIGNED LABELS:")
            for mis in err['misaligned']:
                start, end, label = mis['entity']
                print(f"     - {label}: ({start}, {end}) - {mis['reason']}")

        print()

    print(f"\n💡 How to fix:")
    print(f"{'='*60}")
    print(f"1. Open training_data_labeled.json in a text editor")
    print(f"2. Find the examples listed above (search for the text)")
    print(f"3. Remove duplicate/overlapping entities")
    print(f"4. Fix entity positions that are out of bounds")
    print(f"5. Run this script again to verify")
    print(f"\nOR delete the file and re-label correctly:\n")
    print(f"   rm training_data_labeled.json")
    print(f"   python3 label_data.py --input filtered_training_mixed.json --output training_data_labeled.json --limit 50")
    print(f"{'='*60}\n")

    return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 validate_labels.py <labeled_data.json>")
        print("Example: python3 validate_labels.py training_data_labeled.json")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        valid = validate_labeled_data(file_path)
        sys.exit(0 if valid else 1)
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: '{file_path}' is not valid JSON")
        sys.exit(1)
