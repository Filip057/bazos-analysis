#!/usr/bin/env python3
"""
Test script to demonstrate mileage pattern matching

Tests all variations of mileage formats that users might write on Bazos.cz
"""

from ml.context_aware_patterns import ContextAwarePatterns

def test_mileage_patterns():
    """Test all mileage pattern variations"""
    patterns = ContextAwarePatterns()

    # Test cases: (input_text, expected_value, description)
    test_cases = [
        # Standard formats WITH km
        ("najeto 220 tis km", 220000, "Czech 'thousand' with km"),
        ("najeto 200 000 km", 200000, "Space separator with km"),
        ("najeto 200.000 km", 200000, "Dot separator with km"),
        ("najeto 200_000 km", 200000, "Underscore separator with km"),
        ("najeto 150000 km", 150000, "No separator with km"),
        ("najeto 150km", 150000, "No space before km"),

        # Thousands abbreviations WITHOUT km
        ("najeto 123tis", 123000, "tis without km"),
        ("najeto 123 tis", 123000, "tis with space, no km"),
        ("najeto 123tis.", 123000, "tis with dot, no km"),
        ("najeto 123 tis.", 123000, "tis with space and dot, no km"),
        ("najeto123k", 123000, "k without space or km"),
        ("najeto 123k", 123000, "k with space, no km"),
        ("najeto 123 k", 123000, "k with spaces, no km"),
        ("najeto123t", 123000, "t without space or km"),
        ("najeto 123t", 123000, "t with space, no km"),

        # Thousands abbreviations WITH km
        ("najeto 123tis km", 123000, "tis with km"),
        ("najeto 123 tis km", 123000, "tis with space and km"),
        ("najeto 123tis. km", 123000, "tis with dot and km"),
        ("najeto123k km", 123000, "k with km, no space"),
        ("najeto 123k km", 123000, "k with km and space"),
        ("najeto 123 k km", 123000, "k with spaces and km"),
        ("najeto123t km", 123000, "t with km, no space"),
        ("najeto 123t km", 123000, "t with km and space"),

        # Placeholder formats (xxx)
        ("najeto 123xxx", 123000, "xxx without space or km"),
        ("najeto 123 xxx", 123000, "xxx with space, no km"),
        ("najeto123xxx km", 123000, "xxx with km, no space"),
        ("najeto 123xxx km", 123000, "xxx with space and km"),
        ("najeto 123 xxx km", 123000, "xxx with spaces and km"),

        # Placeholder formats (***)
        ("najeto 123***", 123000, "*** without space or km"),
        ("najeto 123 ***", 123000, "*** with space, no km"),
        ("najeto123*** km", 123000, "*** with km, no space"),
        ("najeto 123*** km", 123000, "*** with space and km"),
        ("najeto 123 *** km", 123000, "*** with spaces and km"),

        # Full number formats
        ("najeto 123.000", 123000, "Dot separator, no km"),
        ("najeto 123 000", 123000, "Space separator, no km"),
        ("najeto 123000", 123000, "No separator, no km"),

        # WITHOUT "najeto" prefix
        ("Auto má 150 tis km", 150000, "Without najeto prefix"),
        ("150k najeto", 150000, "k suffix before najeto"),
        ("150xxx celkem", 150000, "xxx with celkem"),
        ("má 150*** km", 150000, "*** in sentence"),
        ("200.000 km", 200000, "Just dot-separated with km"),
        ("200 000", 200000, "Just space-separated, no km"),

        # Czech word "tisíc"
        ("najeto 123 tisíc km", 123000, "Czech word tisíc with km"),
        ("najeto 123tisíc", 123000, "Czech word tisíc without space"),

        # Edge cases
        ("najeto 1.5tis km", 1500, "Decimal thousands"),
        ("najeto 250k", 250000, "250k format"),
        ("má 85 tis. km", 85000, "85 thousand with dot"),
    ]

    print("=" * 80)
    print("MILEAGE PATTERN TEST RESULTS")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for text, expected_value, description in test_cases:
        matches = patterns.find_mileage(text)

        if matches and matches[0].value == expected_value:
            status = "✓ PASS"
            passed += 1
            match_info = f"Found: {matches[0].text} = {matches[0].value} km (confidence: {matches[0].confidence})"
        elif matches:
            status = "✗ FAIL"
            failed += 1
            match_info = f"Found: {matches[0].text} = {matches[0].value} km (expected: {expected_value})"
        else:
            status = "✗ FAIL"
            failed += 1
            match_info = f"No match found (expected: {expected_value})"

        print(f"{status} | {description}")
        print(f"       Input: '{text}'")
        print(f"       {match_info}")
        print()

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return passed == len(test_cases)


if __name__ == "__main__":
    success = test_mileage_patterns()
    exit(0 if success else 1)
