#!/usr/bin/env python3
"""
Test ML Extraction Without Database
====================================

Simple script to test the ML + context-aware regex extraction system
without needing MySQL connection.

Usage:
    python3 test_ml_extraction.py
"""

import sys
sys.path.insert(0, '/home/user/bazos-analysis')

from ml.production_extractor import ProductionExtractor

# Test examples (Czech car listings)
TEST_EXAMPLES = [
    {
        "id": "1",
        "text": "Škoda Octavia rok výroby 2015, STK do 2027, najeto 150000 km, výkon 110 kW, diesel, servis 2023",
        "expected": {
            "year": 2015,  # NOT 2027 (STK) or 2023 (servis)
            "mileage": 150000,
            "power": 110,
            "fuel": "diesel"
        }
    },
    {
        "id": "2",
        "text": "Volkswagen Golf 1.6 TDI, r.v. 2018, 95 kW, najeto pouze 85 tis. km",
        "expected": {
            "year": 2018,
            "mileage": 85000,
            "power": 95,
            "fuel": "diesel"  # TDI = Turbodiesel, model normalizes to "diesel"
        }
    },
    {
        "id": "3",
        "text": "Ford Focus 2012, 200000 km, 88kw, diesel, STK platnost do 2026",
        "expected": {
            "year": 2012,  # NOT 2026 (STK)
            "mileage": 200000,
            "power": 88,
            "fuel": "diesel"
        }
    },
    {
        "id": "4",
        "text": "BMW 320d 2016 nový motor 2024 90000km 120kW nafta",
        "expected": {
            "year": 2016,  # NOT 2024 (motor replacement)
            "mileage": 90000,
            "power": 120,
            "fuel": "diesel"  # "nafta" = "diesel" in Czech, model normalizes both
        }
    }
]


def test_extraction():
    """Test ML + regex extraction on sample data"""
    print("="*70)
    print("🧪 Testing ML + Context-Aware Regex Extraction")
    print("="*70)
    print()
    print("📝 Note: The ML model NORMALIZES fuel types:")
    print("   - 'TDI', 'nafta', 'diesel' → all become 'diesel'")
    print("   - 'benzín', 'benzin' → 'benzín'")
    print("   - This is CORRECT behavior for database consistency!")
    print()

    # Initialize extractor
    try:
        print("📦 Initializing ProductionExtractor...")
        extractor = ProductionExtractor()
        print("✓ Extractor ready!\n")
    except Exception as e:
        print(f"❌ Failed to initialize extractor: {e}")
        print("\nMake sure you have:")
        print("  1. Trained ML model in ml_models/car_ner/")
        print("  2. Installed spaCy: pip install spacy")
        print("\nIf you don't have a trained model yet, run:")
        print("  python3 -m ml.train_ml_model")
        return

    # Test each example
    passed = 0
    failed = 0

    for example in TEST_EXAMPLES:
        print(f"Test #{example['id']}")
        print("-" * 70)
        print(f"Text: {example['text'][:80]}...")
        print()

        # Extract
        result = extractor.extract(example['text'], car_id=example['id'])

        # Show results
        print("Extracted & Normalized Data:")
        print(f"  Year:       {result.get('year')} (expected: {example['expected'].get('year')})")
        print(f"  Mileage:    {result.get('mileage')} (expected: {example['expected'].get('mileage')})")
        print(f"  Power:      {result.get('power')} (expected: {example['expected'].get('power')})")
        print(f"  Fuel:       {result.get('fuel')} (expected: {example['expected'].get('fuel')})")
        print(f"  Confidence: {result.get('confidence')}")
        print(f"  Agreement:  {result.get('agreement', 'N/A')}")

        # Show raw values if available (debug mode)
        if result.get('raw_values'):
            print(f"\n  Raw (before normalization):")
            print(f"    Fuel: {result['raw_values'].get('fuel')} → {result.get('fuel')}")

        print()

        # Check correctness
        correct = True
        errors = []

        for field in ['year', 'mileage', 'power', 'fuel']:
            expected_val = example['expected'].get(field)
            actual_val = result.get(field)

            # Normalize for comparison
            if isinstance(expected_val, str):
                expected_val = expected_val.lower()
            if isinstance(actual_val, str):
                actual_val = actual_val.lower()

            if expected_val is not None and actual_val != expected_val:
                errors.append(f"{field}: got {actual_val}, expected {expected_val}")
                correct = False

        if correct:
            print("✅ PASSED")
            passed += 1
        else:
            print(f"❌ FAILED: {', '.join(errors)}")
            failed += 1

        print("=" * 70)
        print()

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"Total tests:  {len(TEST_EXAMPLES)}")
    print(f"Passed:       {passed} ✅")
    print(f"Failed:       {failed} ❌")
    print(f"Accuracy:     {passed / len(TEST_EXAMPLES) * 100:.1f}%")
    print("=" * 70)

    # Show extraction statistics
    print("\n📈 Extraction Statistics:")
    extractor.print_stats()

    # Show queue status
    print("\n📁 Queue Status:")
    import json
    try:
        auto_data = json.load(open('auto_training_data.json'))
        review_queue = json.load(open('review_queue.json'))
        print(f"  Auto-training data: {len(auto_data)} examples")
        print(f"  Review queue:       {len(review_queue)} cases")
    except:
        print("  (No queue files yet)")

    print()


if __name__ == "__main__":
    test_extraction()
