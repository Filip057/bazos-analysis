"""
Manual test script for Power Resolution System (no pytest required)
"""

from ml.power_resolver import resolve_power, PowerNormalizer


def test_normalizer():
    """Test power normalization."""
    print("Testing PowerNormalizer...")
    normalizer = PowerNormalizer()

    tests = [
        ("151 kw", "151kw"),
        ("151KW", "151kw"),
        ("110 PS", "110ps"),
        ("110 koní", "110ps"),
        ("", None),
        (None, None),
    ]

    passed = 0
    failed = 0

    for input_val, expected in tests:
        result = normalizer.normalize(input_val)
        if result == expected:
            print(f"  ✓ normalize('{input_val}') = '{result}'")
            passed += 1
        else:
            print(f"  ✗ normalize('{input_val}') = '{result}' (expected '{expected}')")
            failed += 1

    print(f"\nNormalizer: {passed} passed, {failed} failed\n")
    return failed == 0


def test_perfect_agreement():
    """Test when ML and regex agree."""
    print("Testing perfect agreement...")

    resolution = resolve_power("151 kw", "151kw")

    checks = [
        (resolution.ml_raw == "151 kw", "ml_raw preserved"),
        (resolution.regex_raw == "151kw", "regex_raw preserved"),
        (resolution.normalized_ml == "151kw", "normalized_ml correct"),
        (resolution.normalized_regex == "151kw", "normalized_regex correct"),
        (resolution.disagreement_type == "NONE", "no disagreement"),
        (resolution.resolved_value == "151 kw", "resolved_value correct"),
        (resolution.resolution_method == "AUTO_NORMALIZED", "resolution method correct"),
        (resolution.confidence == 0.95, "confidence correct"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            failed += 1

    print(f"\nPerfect agreement: {passed} passed, {failed} failed\n")
    return failed == 0


def test_only_ml():
    """Test when only ML has value."""
    print("Testing only ML present...")

    resolution = resolve_power("151 kw", None)

    checks = [
        (resolution.ml_raw == "151 kw", "ml_raw preserved"),
        (resolution.regex_raw is None, "regex_raw is None"),
        (resolution.disagreement_type == "MINOR_FORMATTING", "minor formatting disagreement"),
        (resolution.resolved_value == "151 kw", "resolved to ML value"),
        (resolution.resolution_method == "ML_PREFERRED", "ML preferred"),
        (resolution.confidence == 0.75, "confidence correct"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            failed += 1

    print(f"\nOnly ML: {passed} passed, {failed} failed\n")
    return failed == 0


def test_only_regex():
    """Test when only regex has value."""
    print("Testing only regex present...")

    resolution = resolve_power(None, "151 kw")

    checks = [
        (resolution.ml_raw is None, "ml_raw is None"),
        (resolution.regex_raw == "151 kw", "regex_raw preserved"),
        (resolution.disagreement_type == "MINOR_FORMATTING", "minor formatting disagreement"),
        (resolution.resolved_value == "151 kw", "resolved to regex value"),
        (resolution.resolution_method == "REGEX_PREFERRED", "regex preferred"),
        (resolution.confidence == 0.80, "confidence correct"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            failed += 1

    print(f"\nOnly regex: {passed} passed, {failed} failed\n")
    return failed == 0


def test_major_disagreement():
    """Test major disagreement."""
    print("Testing major disagreement (prefer regex)...")

    resolution = resolve_power("151 kw", "110 kw", prefer_ml=False)

    checks = [
        (resolution.ml_raw == "151 kw", "ml_raw preserved"),
        (resolution.regex_raw == "110 kw", "regex_raw preserved"),
        (resolution.disagreement_type == "MAJOR", "major disagreement"),
        (resolution.resolved_value == "110 kw", "resolved to regex value"),
        (resolution.resolution_method == "REGEX_PREFERRED", "regex preferred"),
        (resolution.confidence == 0.70, "confidence correct"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            failed += 1

    print(f"\nMajor disagreement: {passed} passed, {failed} failed\n")
    return failed == 0


def test_manual_override():
    """Test manual override."""
    print("Testing manual override...")

    resolution = resolve_power("151 kw", "110 kw", manual_override="145 kw")

    checks = [
        (resolution.resolved_value == "145 kw", "resolved to manual value"),
        (resolution.resolution_method == "MANUAL", "manual method"),
        (resolution.confidence == 1.0, "confidence 1.0"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            failed += 1

    print(f"\nManual override: {passed} passed, {failed} failed\n")
    return failed == 0


def test_to_dict():
    """Test dictionary serialization."""
    print("Testing to_dict()...")

    resolution = resolve_power("151 kw", "151kw")
    result_dict = resolution.to_dict()

    checks = [
        (isinstance(result_dict, dict), "returns dict"),
        (result_dict['ml_raw'] == "151 kw", "ml_raw in dict"),
        (result_dict['regex_raw'] == "151kw", "regex_raw in dict"),
        (result_dict['normalized_ml'] == "151kw", "normalized_ml in dict"),
        (result_dict['normalized_regex'] == "151kw", "normalized_regex in dict"),
        (result_dict['disagreement_type'] == "NONE", "disagreement_type in dict"),
        (result_dict['resolved_value'] == "151 kw", "resolved_value in dict"),
        (result_dict['resolution_method'] == "AUTO_NORMALIZED", "resolution_method in dict"),
        (result_dict['confidence'] == 0.95, "confidence in dict"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            failed += 1

    print(f"\nto_dict: {passed} passed, {failed} failed\n")
    return failed == 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("Power Resolver Test Suite")
    print("=" * 60)
    print()

    all_passed = True

    all_passed = test_normalizer() and all_passed
    all_passed = test_perfect_agreement() and all_passed
    all_passed = test_only_ml() and all_passed
    all_passed = test_only_regex() and all_passed
    all_passed = test_major_disagreement() and all_passed
    all_passed = test_manual_override() and all_passed
    all_passed = test_to_dict() and all_passed

    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
