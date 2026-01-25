#!/usr/bin/env python3
"""
Error Analysis for ML Model
============================

Identifies specific error patterns to guide improvement strategy.
"""

import sys
sys.path.insert(0, '/home/user/bazos-analysis')

import json
import logging
from pathlib import Path
from ml.ml_extractor import CarDataExtractor
from spacy.training import Example

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_errors(model_path: str, test_data_path: str):
    """Analyze what kinds of errors the model makes"""

    # Load model
    extractor = CarDataExtractor(model_path)

    # Load test data
    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    # Convert to proper format if needed
    formatted_data = []
    for item in test_data:
        if isinstance(item, list):
            formatted_data.append(item)
        else:
            text = item.get('text', '')
            entities = item.get('entities', [])
            formatted_data.append((text, {'entities': entities}))

    # Categorize errors
    errors = {
        'false_negatives': [],  # Missed entities
        'false_positives': [],  # Incorrect predictions
        'boundary_errors': [],  # Right entity, wrong boundaries
        'label_confusion': []   # Right span, wrong label
    }

    correct_predictions = 0
    total_predictions = 0
    total_gold_entities = 0

    print("="*70)
    print("🔍 ERROR ANALYSIS")
    print("="*70)
    print()

    for text, annotations in formatted_data[:100]:  # Analyze first 100
        # Get predictions
        doc = extractor.nlp(text)
        predicted_ents = [(ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]

        # Get gold standard
        gold_ents = annotations.get('entities', [])
        total_gold_entities += len(gold_ents)
        total_predictions += len(predicted_ents)

        # Convert to sets for comparison
        pred_set = set(predicted_ents)
        gold_set = set(tuple(e) if isinstance(e, list) else e for e in gold_ents)

        # Find matches
        matches = pred_set & gold_set
        correct_predictions += len(matches)

        # False negatives (missed)
        missed = gold_set - pred_set
        for ent in missed:
            start, end, label = ent
            errors['false_negatives'].append({
                'text': text,
                'entity': text[start:end],
                'label': label,
                'span': (start, end),
                'context': text[max(0, start-20):min(len(text), end+20)]
            })

        # False positives (wrong predictions)
        wrong = pred_set - gold_set
        for ent in wrong:
            start, end, label = ent

            # Check if it's a boundary error (overlaps with gold)
            is_boundary = False
            is_label_confusion = False

            for gold_ent in gold_set:
                g_start, g_end, g_label = gold_ent
                # Check overlap
                if not (end <= g_start or g_end <= start):
                    if label == g_label:
                        is_boundary = True
                    else:
                        is_label_confusion = True
                    break

            error_dict = {
                'text': text,
                'entity': text[start:end],
                'label': label,
                'span': (start, end),
                'context': text[max(0, start-20):min(len(text), end+20)]
            }

            if is_boundary:
                errors['boundary_errors'].append(error_dict)
            elif is_label_confusion:
                errors['label_confusion'].append(error_dict)
            else:
                errors['false_positives'].append(error_dict)

    # Print summary
    print(f"Analyzed: {len(formatted_data[:100])} examples")
    print(f"Total gold entities: {total_gold_entities}")
    print(f"Total predictions: {total_predictions}")
    print(f"Correct predictions: {correct_predictions}")
    print()

    print("="*70)
    print("📊 ERROR BREAKDOWN")
    print("="*70)

    total_errors = sum(len(v) for v in errors.values())

    for error_type, examples in errors.items():
        pct = len(examples) / total_errors * 100 if total_errors > 0 else 0
        print(f"\n{error_type.upper().replace('_', ' ')}: {len(examples)} ({pct:.1f}%)")

        # Show top 3 examples
        for i, example in enumerate(examples[:3], 1):
            print(f"  {i}. [{example['label']}] '{example['entity']}'")
            print(f"     Context: ...{example['context']}...")

    print()
    print("="*70)

    # Save detailed report
    report_path = Path('error_analysis_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Detailed report saved to: {report_path}")

    # Recommendations
    print()
    print("="*70)
    print("💡 RECOMMENDATIONS")
    print("="*70)

    fn_pct = len(errors['false_negatives']) / total_errors * 100 if total_errors > 0 else 0
    fp_pct = len(errors['false_positives']) / total_errors * 100 if total_errors > 0 else 0

    if fn_pct > 30:
        print("⚠️  HIGH FALSE NEGATIVES (missed entities)")
        print("   → Add more diverse training examples")
        print("   → Include more edge cases and rare formats")

    if fp_pct > 20:
        print("⚠️  HIGH FALSE POSITIVES (wrong predictions)")
        print("   → Add negative examples (text with NO entities)")
        print("   → Increase training iterations")

    if len(errors['boundary_errors']) > 10:
        print("⚠️  BOUNDARY ALIGNMENT ISSUES")
        print("   → Review tokenization in Czech")
        print("   → Check entity span annotations carefully")

    if len(errors['label_confusion']) > 5:
        print("⚠️  LABEL CONFUSION (wrong entity type)")
        print("   → Add more examples of confused labels")
        print("   → Consider entity patterns (e.g., YEAR vs MILEAGE)")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze ML model errors")
    parser.add_argument("--model", default="./ml_models/car_ner", help="Model path")
    parser.add_argument("--data", default="./training_data_labeled.json", help="Test data")

    args = parser.parse_args()

    analyze_errors(args.model, args.data)
