#!/usr/bin/env python3
"""
Test improved extraction patterns on user-provided failed examples
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.context_aware_patterns import ContextAwarePatterns

def test_extraction():
    patterns = ContextAwarePatterns()

    print("=" * 70)
    print("TESTING IMPROVED EXTRACTION PATTERNS")
    print("=" * 70)

    # User-provided failed examples
    test_cases = [
        {
            'name': 'YEAR: do provozu 10.6.2013',
            'text': 'do provozu 10.6.2013',
            'expected_year': 2013,
            'expected_mileage': None
        },
        {
            'name': 'YEAR: V provozu od: 8/2009',
            'text': 'V provozu od: 8/2009',
            'expected_year': 2009,
            'expected_mileage': None
        },
        {
            'name': 'YEAR: uveden do provozu 05/2017',
            'text': 'uveden do provozu 05/2017',
            'expected_year': 2017,
            'expected_mileage': None
        },
        {
            'name': 'MILEAGE: NAJETO SKUTEČNÝCH 142.981KM',
            'text': 'NAJETO SKUTEČNÝCH A JASNĚ DOLOŽENÝCH 142.981KM',
            'expected_year': None,
            'expected_mileage': 142981
        },
        {
            'name': 'MILEAGE: palivo Benzin, najeto: 201.455 km',
            'text': 'palivo: Benzin\nnajeto: 201.455 km',
            'expected_year': None,
            'expected_mileage': 201455
        },
        {
            'name': 'MILEAGE: najeto 54000',
            'text': 'najeto 54000',
            'expected_year': None,
            'expected_mileage': 54000
        },
        {
            'name': 'MILEAGE: najeto: 238.834 km',
            'text': 'najeto: 238.834 km',
            'expected_year': None,
            'expected_mileage': 238834
        },
        {
            'name': 'MILEAGE: aktuální nájezd je 59.900 km',
            'text': 'aktuální nájezd je 59.900 km',
            'expected_year': None,
            'expected_mileage': 59900
        },
        {
            'name': 'COMBINED: Mazda 2015, do provozu 2015, najeto 150000 km',
            'text': 'Mazda 2015, do provozu 2015, najeto 150000 km',
            'expected_year': 2015,
            'expected_mileage': 150000
        }
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST: {test['name']}")
        print(f"{'='*70}")
        print(f"Text: {test['text']!r}")

        # Extract year
        years = patterns.find_years(test['text'])
        extracted_year = years[0].value if years else None

        # Extract mileage
        mileage_matches = patterns.find_mileage(test['text'])
        extracted_mileage = mileage_matches[0].value if mileage_matches else None

        # Check results
        year_pass = extracted_year == test['expected_year']
        mileage_pass = extracted_mileage == test['expected_mileage']

        print(f"\nRESULTS:")
        print(f"  Year:    {extracted_year} {'✅' if year_pass else '❌'} (expected: {test['expected_year']})")
        if years and not year_pass:
            print(f"           Found: {years[0].text} (confidence: {years[0].confidence}, type: {years[0].pattern_type})")

        print(f"  Mileage: {extracted_mileage} {'✅' if mileage_pass else '❌'} (expected: {test['expected_mileage']})")
        if mileage_matches and not mileage_pass:
            print(f"           Found: {mileage_matches[0].text} = {mileage_matches[0].value} (confidence: {mileage_matches[0].confidence})")

        if year_pass and mileage_pass:
            print("\n  ✅ TEST PASSED")
            passed += 1
        else:
            print("\n  ❌ TEST FAILED")
            failed += 1

    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"  Passed: {passed}/{len(test_cases)}")
    print(f"  Failed: {failed}/{len(test_cases)}")
    print(f"  Success rate: {passed/len(test_cases)*100:.1f}%")

    if passed == len(test_cases):
        print("\n  🎉 ALL TESTS PASSED! Extraction patterns are working!")
    else:
        print(f"\n  ⚠️  {failed} tests failed. Review patterns above.")

    print(f"{'='*70}\n")

if __name__ == "__main__":
    test_extraction()
