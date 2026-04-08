#!/usr/bin/env python3
"""
Combine Labeled Data + Retrain Model
-------------------------------------
Combines new GPT-labeled data with existing labeled data,
then retrains the ML model.

Usage:
    python3 combine_and_train.py

    Or with custom files:
    python3 combine_and_train.py --new auto_labeled_193.json --existing training_data_fixed.json
"""

import json
import argparse
import subprocess
import sys
from pathlib import Path

def load_json(file_path):
    """Load JSON file"""
    print(f"📂 Loading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   Loaded {len(data)} examples")
    return data

def validate_spacy_format(data, file_name):
    """Validate data is in spaCy training format"""
    print(f"🔍 Validating {file_name}...")

    if not isinstance(data, list):
        print(f"   ❌ ERROR: Not a list!")
        return False

    errors = 0
    for i, example in enumerate(data):
        if not isinstance(example, list) or len(example) != 2:
            print(f"   ❌ Example {i}: Not a [text, {{entities: ...}}] pair")
            errors += 1
            continue

        text, annotations = example

        if not isinstance(text, str):
            print(f"   ❌ Example {i}: Text is not a string")
            errors += 1

        if not isinstance(annotations, dict) or 'entities' not in annotations:
            print(f"   ❌ Example {i}: Missing 'entities' key")
            errors += 1
            continue

        entities = annotations['entities']
        if not isinstance(entities, list):
            print(f"   ❌ Example {i}: Entities is not a list")
            errors += 1
            continue

        # Check entity format
        for j, entity in enumerate(entities):
            if not isinstance(entity, list) or len(entity) != 3:
                print(f"   ❌ Example {i}, Entity {j}: Not [start, end, label] format")
                errors += 1
                continue

            start, end, label = entity

            if not isinstance(start, int) or not isinstance(end, int):
                print(f"   ❌ Example {i}, Entity {j}: Positions not integers")
                errors += 1

            if not isinstance(label, str):
                print(f"   ❌ Example {i}, Entity {j}: Label not string")
                errors += 1

            # Check positions match text
            if start < 0 or end > len(text) or start >= end:
                print(f"   ❌ Example {i}, Entity {j}: Invalid positions [{start}, {end}] for text length {len(text)}")
                errors += 1

    if errors == 0:
        print(f"   ✅ Format valid!")
        return True
    else:
        print(f"   ⚠️  Found {errors} validation errors")
        return False

def combine_datasets(new_data, existing_data, output_file):
    """Combine two datasets and deduplicate"""
    print(f"\n🔗 Combining datasets...")

    # Create set of existing texts for deduplication
    existing_texts = {example[0] for example in existing_data}

    # Add new examples that don't exist
    added = 0
    duplicates = 0

    for example in new_data:
        text = example[0]
        if text not in existing_texts:
            existing_data.append(example)
            existing_texts.add(text)
            added += 1
        else:
            duplicates += 1

    print(f"   Added {added} new examples")
    print(f"   Skipped {duplicates} duplicates")
    print(f"   Total: {len(existing_data)} examples")

    # Save combined dataset
    print(f"\n💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ Saved!")

    return existing_data

def show_statistics(data):
    """Show dataset statistics"""
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total examples: {len(data)}")

    # Count examples with entities
    with_entities = sum(1 for ex in data if ex[1]['entities'])
    print(f"   With entities: {with_entities} ({with_entities/len(data)*100:.1f}%)")

    # Count entity types
    entity_counts = {}
    total_entities = 0

    for ex in data:
        for entity in ex[1]['entities']:
            label = entity[2]
            entity_counts[label] = entity_counts.get(label, 0) + 1
            total_entities += 1

    print(f"   Total entities: {total_entities}")
    print(f"   Avg per example: {total_entities/len(data):.1f}")
    print(f"\n   Entity types:")
    for label, count in sorted(entity_counts.items(), key=lambda x: -x[1]):
        print(f"     {label}: {count} ({count/total_entities*100:.1f}%)")

def train_model(training_file, iterations=30):
    """Train ML model"""
    print(f"\n🤖 Training ML Model...")
    print(f"=" * 70)

    cmd = [
        'python3', '-m', 'ml.train_ml_model',
        '--data', training_file,
        '--iterations', str(iterations),
        '--output', 'ml_models/car_ner_retrained'
    ]

    print(f"Command: {' '.join(cmd)}")
    print(f"=" * 70)

    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ Training completed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Training failed: {e}")
        return False

def test_model(model_path='ml_models/car_ner_retrained'):
    """Test trained model"""
    print(f"\n🧪 Testing Model...")
    print(f"=" * 70)

    cmd = [
        'python3', '-m', 'ml.test_ml_model',
        '--model', model_path
    ]

    print(f"Command: {' '.join(cmd)}")
    print(f"=" * 70)

    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ Testing completed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Testing failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Combine labeled data and retrain ML model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults
  python3 combine_and_train.py

  # Custom files
  python3 combine_and_train.py --new auto_labeled_193.json --existing training_data_fixed.json

  # Skip training (just combine)
  python3 combine_and_train.py --no-train

  # Custom iterations
  python3 combine_and_train.py --iterations 50

Workflow:
  1. Load new labeled data (from GPT)
  2. Load existing labeled data
  3. Validate both datasets
  4. Combine (deduplicate)
  5. Save to training_data_final.json
  6. Train ML model (30 iterations)
  7. Test model (show F1 score)
        """
    )

    parser.add_argument('--new', default='auto_labeled_193.json', help='New labeled data from GPT (default: auto_labeled_193.json)')
    parser.add_argument('--existing', default='training_data_fixed.json', help='Existing labeled data (default: training_data_fixed.json)')
    parser.add_argument('--output', default='training_data_final.json', help='Combined output file (default: training_data_final.json)')
    parser.add_argument('--iterations', type=int, default=30, help='Training iterations (default: 30)')
    parser.add_argument('--no-train', action='store_true', help='Skip training (just combine data)')
    parser.add_argument('--no-test', action='store_true', help='Skip testing (just train)')

    args = parser.parse_args()

    print("=" * 70)
    print("🚀 COMBINE & RETRAIN WORKFLOW")
    print("=" * 70)

    # Check files exist
    if not Path(args.new).exists():
        print(f"\n❌ ERROR: {args.new} not found!")
        print(f"\n💡 Did you complete GPT labeling?")
        print(f"   See LABELING_INSTRUCTIONS.md for help.")
        sys.exit(1)

    if not Path(args.existing).exists():
        print(f"\n❌ ERROR: {args.existing} not found!")
        print(f"\n💡 Try using: training_data_combined.json or training_data_labeled.json")
        sys.exit(1)

    # Load data
    new_data = load_json(args.new)
    existing_data = load_json(args.existing)

    # Validate
    new_valid = validate_spacy_format(new_data, args.new)
    existing_valid = validate_spacy_format(existing_data, args.existing)

    if not new_valid or not existing_valid:
        print(f"\n❌ Validation failed! Fix errors and try again.")
        sys.exit(1)

    # Combine
    combined = combine_datasets(new_data, existing_data, args.output)

    # Show stats
    show_statistics(combined)

    # Train
    if not args.no_train:
        success = train_model(args.output, args.iterations)

        if success and not args.no_test:
            test_model()
        elif success:
            print(f"\n✅ Training completed! Model saved to ml_models/car_ner_retrained")
            print(f"   Run manually: python3 -m ml.test_ml_model --model ml_models/car_ner_retrained")
    else:
        print(f"\n✅ Data combined! Skipping training.")
        print(f"   To train: python3 -m ml.train_ml_model --data {args.output}")

    print(f"\n" + "=" * 70)
    print(f"🎉 DONE!")
    print(f"=" * 70)

if __name__ == '__main__':
    main()
