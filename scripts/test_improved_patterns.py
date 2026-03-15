#!/usr/bin/env python3
"""
Test improved patterns on gap_analysis.csv examples

This validates that new patterns fix the gaps found in gap analysis.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.context_aware_patterns import ContextAwarePatterns

# Test cases from gap_analysis.csv
TEST_CASES = [
    # YEAR gaps
    {
        'id': 27,
        'context': "6 Wagon 2.0 Skyactiv 121 kW08/2016 (Německo) | 141 209 km | Benz",
        'expected_year': 2016,
        'expected_mileage': 141209,
    },
    {
        'id': 47,
        'context': "Německu (rodina)Rok výroby 07/2020 provoz 10/2020Stav tachometru",
        'expected_year': 2020,
    },
    {
        'id': 56,
        'context': "5 2.0 121kW AD´VANTAGE r.v.01/2022 NAVI,LED,HEAD UP",
        'expected_year': 2022,
    },
    {
        'id': 75,
        'context': " 2.5 KOMBI SPORTS LINE r.v.09/2020 MATRIX,NAVI",
        'expected_year': 2020,
    },
    {
        'id': 78,
        'context': "abriolet Roadster,rok výr. 12/2010 (facelift) najeto 163.000 km",
        'expected_year': 2010,
        'expected_mileage': 163000,
    },
    {
        'id': 102,
        'context': "Mazda 3 1.6i 77kw,1.reg.2012,klima",
        'expected_year': 2012,
    },

    # MILEAGE gaps (dot-separated thousands)
    {
        'id': 2,
        'context': "istorií do roku 2026 v ČR. Do 56.000km do roku 2019 servisováno u Ma",
        'expected_mileage': 56000,
    },
    {
        'id': 7,
        'context': "MAZDA R17 - POSLEDNÍ SERVIS PŘI 196.395KM DNE 15.09.2025 - MOŽNOST SE D",
        'expected_mileage': 196395,
    },
    {
        'id': 9,
        'context': " SKYACTIV-G 118kW AWD-12/2015-90.708KM-NAVI-",
        'expected_mileage': 90708,
    },
    {
        'id': 11,
        'context': "A 6 2.0 SKYACTIV-G 121kW-2013-149.720KM-VÝHŘEV,KAMERA-",
        'expected_mileage': 149720,
    },
    {
        'id': 16,
        'context': "SKYACTIV-G 110kW AUTOMAT-2021-46.388KM-NAVI-",
        'expected_mileage': 46388,
    },

    # FALSE POSITIVES - should NOT extract (kW as mileage)
    {
        'id': 3,
        'context': "MAZDA 6 2.0i 121KW BENZIN MANUÁL-XENON-KUŽE-KAM",
        'expected_mileage': None,  # 121KW is POWER, not mileage!
    },
    {
        'id': 8,
        'context': "m atmosferickým motorem g160 (118 Kw, kroutící moment 200 Nm), kt",
        'expected_mileage': None,  # 118 Kw is POWER!
    },
]

def test_patterns():
    """Test improved patterns"""
    patterns = ContextAwarePatterns()

    print("=" * 80)
    print("TESTING IMPROVED PATTERNS (from gap_analysis.csv)")
    print("=" * 80)

    total = 0
    passed = 0
    failed = 0

    for test in TEST_CASES:
        total += 1
        test_id = test['id']
        context = test['context']
        expected_year = test.get('expected_year')
        expected_mileage = test.get('expected_mileage')

        print(f"\n[TEST {total}] ID={test_id}")
        print(f"  Context: {context[:80]}...")

        # Test YEAR
        if expected_year is not None:
            years = patterns.find_years(context)
            found_year = years[0].value if years else None

            if found_year == expected_year:
                print(f"  ✅ YEAR: {found_year} (expected: {expected_year})")
                passed += 1
            else:
                print(f"  ❌ YEAR: {found_year} (expected: {expected_year})")
                if years:
                    print(f"     Pattern: {years[0].pattern_type}, confidence: {years[0].confidence}")
                failed += 1

        # Test MILEAGE
        if 'expected_mileage' in test:
            mileages = patterns.find_mileage(context)
            found_mileage = mileages[0].value if mileages else None

            if found_mileage == expected_mileage:
                print(f"  ✅ MILEAGE: {found_mileage} (expected: {expected_mileage})")
                passed += 1
            else:
                print(f"  ❌ MILEAGE: {found_mileage} (expected: {expected_mileage})")
                if mileages:
                    print(f"     Pattern: {mileages[0].pattern_type}, confidence: {mileages[0].confidence}")
                    print(f"     Matched text: '{mileages[0].text}'")
                failed += 1

    # Summary
    print(f"\n{'=' * 80}")
    print("TEST RESULTS")
    print(f"{'=' * 80}")
    print(f"  Total tests: {total}")
    print(f"  Passed:      {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed:      {failed} ({failed/total*100:.1f}%)")
    print(f"{'=' * 80}\n")

    if failed == 0:
        print("✅ ALL TESTS PASSED! Patterns are ready for re-extraction!")
    else:
        print(f"❌ {failed} tests failed. Review patterns and fix.")

if __name__ == "__main__":
    test_patterns()
