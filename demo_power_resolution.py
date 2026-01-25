"""
Power Resolution System Demonstration

This script demonstrates the new power resolution system with real-world
car listing examples showing various scenarios:
- Perfect agreement between ML and regex
- Minor formatting differences
- Major disagreements
- One source missing
"""

import json
from ml.power_resolver import resolve_power


def print_resolution(scenario_name: str, ml_raw: str, regex_raw: str, description: str):
    """Print a formatted resolution result."""
    print("=" * 70)
    print(f"Scenario: {scenario_name}")
    print("=" * 70)
    print(f"Description: {description}")
    print(f"\nInputs:")
    print(f"  ML Raw:    {ml_raw}")
    print(f"  Regex Raw: {regex_raw}")

    resolution = resolve_power(ml_raw, regex_raw)

    print(f"\nResolution:")
    print(f"  Normalized ML:      {resolution.normalized_ml}")
    print(f"  Normalized Regex:   {resolution.normalized_regex}")
    print(f"  Disagreement Type:  {resolution.disagreement_type}")
    print(f"  Resolved Value:     {resolution.resolved_value}")
    print(f"  Resolution Method:  {resolution.resolution_method}")
    print(f"  Confidence:         {resolution.confidence}")

    print("\nJSON Output:")
    print(json.dumps(resolution.to_dict(), indent=2, ensure_ascii=False))
    print("\n")


def main():
    """Run demonstration scenarios."""
    print("\n" + "=" * 70)
    print("POWER RESOLUTION SYSTEM DEMONSTRATION")
    print("=" * 70)
    print()

    # Scenario 1: Perfect agreement (minor formatting only)
    print_resolution(
        "Perfect Agreement",
        ml_raw="151 kw",
        regex_raw="151kw",
        description="ML and regex agree on value, minor spacing difference"
    )

    # Scenario 2: Both formats same
    print_resolution(
        "Identical Extractions",
        ml_raw="110 KW",
        regex_raw="110 KW",
        description="Both extract exactly the same format"
    )

    # Scenario 3: Only ML found power
    print_resolution(
        "ML Only",
        ml_raw="145 kw",
        regex_raw=None,
        description="ML found power value, regex didn't detect it"
    )

    # Scenario 4: Only regex found power
    print_resolution(
        "Regex Only",
        ml_raw=None,
        regex_raw="85 kW",
        description="Regex found power value, ML missed it"
    )

    # Scenario 5: Major disagreement - different values
    print_resolution(
        "Major Disagreement",
        ml_raw="151 kw",
        regex_raw="110 kw",
        description="Different power values extracted (could be multiple mentions in text)"
    )

    # Scenario 6: Different units (same number)
    print_resolution(
        "Different Units",
        ml_raw="110 kw",
        regex_raw="110 ps",
        description="Same number but different units (kW vs PS)"
    )

    # Scenario 7: Neither found power
    print_resolution(
        "Both Missing",
        ml_raw=None,
        regex_raw=None,
        description="Neither ML nor regex found power value"
    )

    # Scenario 8: Case variations
    print_resolution(
        "Case Variations",
        ml_raw="150 KW",
        regex_raw="150 kw",
        description="Different case in unit name"
    )

    # Real-world scenario 9: Typical car listing
    print("=" * 70)
    print("Real-World Example: Complete Car Listing")
    print("=" * 70)
    print("Text: 'Škoda Octavia 2015, 110 kW, diesel, STK do 2027'")
    print()

    # Simulate what ML and regex might extract
    ml_extracted = "110 KW"
    regex_extracted = "110 kW"

    resolution = resolve_power(ml_extracted, regex_extracted)

    print(f"ML extracted:    '{ml_extracted}'")
    print(f"Regex extracted: '{regex_extracted}'")
    print(f"\nResolution Result:")
    print(f"  ✓ Agreement:   {resolution.disagreement_type}")
    print(f"  ✓ Final Value: {resolution.resolved_value}")
    print(f"  ✓ Confidence:  {resolution.confidence}")
    print()

    # Show how this integrates with database storage
    from ml.power_resolver import PowerNormalizer
    normalizer = PowerNormalizer()
    numeric_value = normalizer.extract_numeric(resolution.resolved_value)
    print(f"For database storage (integer kW): {numeric_value}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
The power resolution system provides:

1. PRESERVATION: Raw ML and regex values never modified
2. NORMALIZATION: Standardized format for comparison (e.g., "151kw")
3. CLASSIFICATION: Disagreement types (NONE, MINOR_FORMATTING, MAJOR)
4. RESOLUTION: Intelligent value selection with confidence scoring
5. TRANSPARENCY: Full metadata for training and debugging

Benefits:
- ML model can retrain on original raw formats
- Robust comparison handles formatting variations
- Clear confidence scores for downstream decisions
- Audit trail for all disagreements
- Easy manual review when needed
    """)


if __name__ == "__main__":
    main()
