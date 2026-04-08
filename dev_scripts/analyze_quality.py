#!/usr/bin/env python3
"""
Analyze existing labeled data quality
"""

import json
import sys

def analyze_labeled_data(file_path):
    """Analyze quality of labeled training data"""

    print("=" * 70)
    print("🔍 ANALYZING LABELED DATA QUALITY")
    print("=" * 70)

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\nTotal examples: {len(data)}")

    # Stats
    entity_counts = {
        'YEAR': 0,
        'MILEAGE': 0,
        'FUEL': 0,
        'POWER': 0
    }

    examples_with_all_entities = 0
    examples_with_no_entities = 0
    incomplete_examples = []

    for i, item in enumerate(data):
        # Handle different formats
        if isinstance(item, dict) and 'data' in item:
            # Format: {"data": [text, {entities: ...}], ...}
            text, annotations = item['data']
        elif isinstance(item, list) and len(item) == 2:
            # Format: [text, {entities: ...}]
            text, annotations = item
        else:
            print(f"⚠️  Unknown format at index {i}")
            continue

        entities = annotations.get('entities', [])

        if not entities:
            examples_with_no_entities += 1
            continue

        # Count entity types in this example
        found_entities = set()
        for entity in entities:
            if len(entity) >= 3:
                label = entity[2]
                entity_counts[label] = entity_counts.get(label, 0) + 1
                found_entities.add(label)

        # Check completeness
        if len(found_entities) == 4:
            examples_with_all_entities += 1
        elif len(found_entities) > 0:
            incomplete_examples.append({
                'index': i,
                'found': list(found_entities),
                'missing': list(set(['YEAR', 'MILEAGE', 'FUEL', 'POWER']) - found_entities),
                'text_preview': text[:100]
            })

    # Results
    print(f"\n📊 ENTITY DISTRIBUTION:")
    total_entities = sum(entity_counts.values())
    for label, count in sorted(entity_counts.items()):
        percentage = (count / len(data)) * 100 if len(data) > 0 else 0
        print(f"  {label:8s}: {count:4d} ({percentage:.1f}% of examples)")

    print(f"\n📈 COMPLETENESS:")
    print(f"  All 4 entities:   {examples_with_all_entities:4d} ({examples_with_all_entities/len(data)*100:.1f}%)")
    print(f"  Incomplete:       {len(incomplete_examples):4d} ({len(incomplete_examples)/len(data)*100:.1f}%)")
    print(f"  No entities:      {examples_with_no_entities:4d} ({examples_with_no_entities/len(data)*100:.1f}%)")

    # Show incomplete examples
    if incomplete_examples:
        print(f"\n⚠️  INCOMPLETE EXAMPLES (first 5):")
        for ex in incomplete_examples[:5]:
            print(f"\n  Example {ex['index']}:")
            print(f"    Found: {', '.join(ex['found'])}")
            print(f"    Missing: {', '.join(ex['missing'])}")
            print(f"    Text: {ex['text_preview']}...")

    # Quality score
    completeness_rate = examples_with_all_entities / len(data) * 100 if len(data) > 0 else 0

    print(f"\n" + "=" * 70)
    print(f"📊 QUALITY SCORE: {completeness_rate:.1f}%")

    if completeness_rate >= 80:
        print(f"✅ GOOD quality! Ready for more data.")
    elif completeness_rate >= 60:
        print(f"⚠️  MEDIUM quality. Consider fixing incomplete examples.")
    else:
        print(f"❌ LOW quality! Fix existing data before adding more.")

    print("=" * 70)

    return {
        'total': len(data),
        'complete': examples_with_all_entities,
        'incomplete': len(incomplete_examples),
        'empty': examples_with_no_entities,
        'quality_score': completeness_rate
    }

if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Try common files
        import os
        candidates = [
            'training_data_fixed.json',
            'training_data_combined.json',
            'auto_training_data.json',
            'manual_review_data.json'
        ]

        file_path = None
        for candidate in candidates:
            if os.path.exists(candidate):
                file_path = candidate
                break

        if not file_path:
            print("❌ No labeled data file found!")
            print("\nUsage: python3 analyze_quality.py <file.json>")
            sys.exit(1)

    print(f"Analyzing: {file_path}\n")
    analyze_labeled_data(file_path)
