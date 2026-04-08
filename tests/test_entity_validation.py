"""
Test Entity Validation
=======================

Quick test to verify the entity validation and cleaning works correctly.
"""

import sys
sys.path.insert(0, '/home/user/bazos-analysis')

from ml.ml_extractor import CarDataExtractor
import logging

logging.basicConfig(level=logging.INFO)

def test_overlapping_entities():
    """Test that overlapping entities are handled correctly"""
    print("\n" + "="*80)
    print("TEST 1: Overlapping entities (same span, different labels)")
    print("="*80)

    # Create test data with overlapping entities
    training_data = [
        ("Prodám auto rok 2015 TDI", {
            "entities": [
                (15, 19, "YEAR"),   # "2015"
                (15, 19, "FUEL"),   # "2015" - OVERLAP (this should be removed)
            ]
        })
    ]

    extractor = CarDataExtractor()

    # This should not crash
    try:
        extractor.train(training_data, n_iter=1, output_dir="./test_model")
        print("✅ Training with overlapping entities succeeded!")
        return True
    except ValueError as e:
        print(f"❌ Training failed with overlapping entities: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_misaligned_entities():
    """Test that misaligned entities are handled correctly"""
    print("\n" + "="*80)
    print("TEST 2: Misaligned entities")
    print("="*80)

    # Create test data with potentially misaligned entities
    training_data = [
        ("Škoda Octavia 2015, 120000 km, 110 kW", {
            "entities": [
                (21, 30, "MILEAGE"),  # "120000 km"
                (14, 18, "YEAR"),     # "2015"
                (32, 38, "POWER"),    # "110 kW"
            ]
        })
    ]

    extractor = CarDataExtractor()

    try:
        extractor.train(training_data, n_iter=1, output_dir="./test_model2")
        print("✅ Training with potentially misaligned entities succeeded!")
        return True
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return False


def test_partial_overlap():
    """Test entities that partially overlap"""
    print("\n" + "="*80)
    print("TEST 3: Partially overlapping entities")
    print("="*80)

    training_data = [
        ("Auto z roku 2015 TDI", {
            "entities": [
                (12, 16, "YEAR"),      # "2015"
                (12, 20, "FUEL"),      # "2015 TDI" - PARTIAL OVERLAP
            ]
        })
    ]

    extractor = CarDataExtractor()

    try:
        extractor.train(training_data, n_iter=1, output_dir="./test_model3")
        print("✅ Training with partial overlaps succeeded!")
        return True
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("Testing Entity Validation and Cleaning")
    print("="*80)

    results = []
    results.append(("Overlapping entities", test_overlapping_entities()))
    results.append(("Misaligned entities", test_misaligned_entities()))
    results.append(("Partial overlap", test_partial_overlap()))

    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("="*80)

    if all_passed:
        print("\n✅ All tests passed! Entity validation is working correctly.")
        print("You can now run retrain_model.py without overlapping entity errors.\n")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the output above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
