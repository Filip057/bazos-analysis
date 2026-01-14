"""
Analyze Labeled Data Quality
=============================

Checks the quality of your labeled training data.

Usage:
    python3 analyze_labeled_data.py training_data_labeled.json
"""

import json
import sys
from collections import Counter


def analyze_labeled_data(file_path: str):
    """Analyze the quality of labeled training data"""

    print(f"\n{'='*60}")
    print(f"Labeled Data Quality Analysis")
    print(f"{'='*60}")
    print(f"File: {file_path}\n")

    # Load labeled data
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_examples = len(data)
    total_entities = 0
    examples_with_entities = 0
    examples_without_entities = 0
    entity_types = Counter()

    # Analyze each example
    for item in data:
        # Handle both tuple format (text, {"entities": [...]}) and dict format
        if isinstance(item, (list, tuple)):
            text, annotations = item
            entities = annotations.get('entities', [])
        else:
            text = item.get('text', '')
            entities = item.get('entities', [])

        if entities:
            examples_with_entities += 1
            total_entities += len(entities)

            # Count entity types
            for start, end, label in entities:
                entity_types[label] += 1
        else:
            examples_without_entities += 1

    # Calculate statistics
    avg_entities = total_entities / total_examples if total_examples > 0 else 0

    # Print results
    print(f"📊 Overall Statistics:")
    print(f"{'='*60}")
    print(f"Total examples:           {total_examples}")
    print(f"Examples with entities:   {examples_with_entities} ({examples_with_entities/total_examples*100:.1f}%)")
    print(f"Examples without entities:{examples_without_entities} ({examples_without_entities/total_examples*100:.1f}%)")
    print(f"Total entities labeled:   {total_entities}")
    print(f"Average entities/example: {avg_entities:.2f}")
    print(f"{'='*60}\n")

    # Print entity type breakdown
    if entity_types:
        print(f"🏷️  Entity Type Distribution:")
        print(f"{'='*60}")
        for entity_type, count in entity_types.most_common():
            percentage = count / total_entities * 100 if total_entities > 0 else 0
            print(f"{entity_type:12s}: {count:4d} ({percentage:5.1f}%)")
        print(f"{'='*60}\n")

    # Data quality assessment
    print(f"✅ Quality Assessment:")
    print(f"{'='*60}")

    if avg_entities >= 2.0:
        print(f"✅ Excellent! Average {avg_entities:.2f} entities per example.")
        print(f"   Your data is high quality for training.")
    elif avg_entities >= 1.0:
        print(f"⚠️  Good. Average {avg_entities:.2f} entities per example.")
        print(f"   Aim for 2+ entities per example for best results.")
    elif avg_entities >= 0.5:
        print(f"⚠️  Low quality. Average {avg_entities:.2f} entities per example.")
        print(f"   Many examples are empty. Use filtered data!")
    else:
        print(f"❌ Poor quality. Average {avg_entities:.2f} entities per example.")
        print(f"   Most examples are empty. Filter your data first!")

    print(f"{'='*60}\n")

    # Show sample labeled examples
    if examples_with_entities > 0:
        print(f"📝 Sample Labeled Examples (first 3):\n")
        shown = 0
        for i, item in enumerate(data):
            # Handle both tuple and dict format
            if isinstance(item, (list, tuple)):
                text, annotations = item
                entities = annotations.get('entities', [])
            else:
                text = item.get('text', '')
                entities = item.get('entities', [])

            if entities and shown < 3:
                shown += 1

                print(f"{shown}. Text: {text[:60]}...")
                print(f"   Entities: {len(entities)}")
                for start, end, label in entities:
                    entity_text = text[start:end]
                    print(f"      - {label}: '{entity_text}'")
                print()

    # Recommendations
    print(f"\n💡 Recommendations:")
    print(f"{'='*60}")

    if examples_without_entities > examples_with_entities:
        print(f"⚠️  Too many empty examples ({examples_without_entities}/{total_examples})")
        print(f"   Solution: Use filter_training_data.py first!")

    if total_entities < 100:
        print(f"⚠️  Only {total_entities} entities total")
        print(f"   Recommendation: Label at least 50-100 examples with 2+ entities each")
        print(f"   Target: 150-300 total entities")

    if total_entities >= 150:
        print(f"✅ You have {total_entities} entities - ready to train!")
        print(f"   Next step: python3 train_ml_model.py --data {file_path}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_labeled_data.py <labeled_data.json>")
        print("Example: python3 analyze_labeled_data.py training_data_labeled.json")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        analyze_labeled_data(file_path)
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: '{file_path}' is not valid JSON")
        sys.exit(1)
