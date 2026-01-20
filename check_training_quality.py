#!/usr/bin/env python3
"""
Check Training Data Quality
============================

Analyzes training data for:
1. Fuel type inconsistencies (nafta vs diesel)
2. Contradictions (TDI + benzín)
3. Normalization issues

Usage:
    python3 check_training_quality.py training_data_labeled.json
"""

import json
import sys
import re
from collections import Counter, defaultdict

def load_training_data(filename):
    """Load training data from JSON file"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_fuel_consistency(training_data):
    """Check for fuel type synonyms that should be normalized"""

    print("="*70)
    print("🔍 Checking Fuel Type Consistency")
    print("="*70)

    fuel_labels = defaultdict(list)

    # Collect all fuel labels and their contexts
    for text, annotations in training_data:
        entities = annotations.get('entities', [])

        for start, end, label in entities:
            if label == 'FUEL':
                fuel_value = text[start:end].lower().strip()
                fuel_labels[fuel_value].append(text[:100] + "...")

    print(f"\nFound {len(fuel_labels)} unique fuel labels:\n")

    for fuel, examples in sorted(fuel_labels.items(), key=lambda x: -len(x[1])):
        print(f"  '{fuel}': {len(examples)} times")

    print("\n" + "-"*70)
    print("⚠️  Potential Normalization Issues:")
    print("-"*70)

    # Check for synonyms
    diesel_variants = ['diesel', 'nafta', 'tdi', 'motorová nafta', 'td', 'naft']
    benzin_variants = ['benzín', 'benzin', 'b', 'gas']

    diesel_found = {k: v for k, v in fuel_labels.items() if any(variant in k for variant in diesel_variants)}
    benzin_found = {k: v for k, v in fuel_labels.items() if any(variant in k for variant in benzin_variants)}

    if len(diesel_found) > 1:
        print("\n❌ DIESEL SYNONYMS (should all be 'diesel'):")
        for fuel, examples in diesel_found.items():
            print(f"   '{fuel}': {len(examples)} examples")
            if len(examples) <= 2:
                for ex in examples:
                    print(f"      → {ex}")

    if len(benzin_found) > 1:
        print("\n❌ BENZÍN VARIANTS (should all be 'benzín'):")
        for fuel, examples in benzin_found.items():
            print(f"   '{fuel}': {len(examples)} examples")
            if len(examples) <= 2:
                for ex in examples:
                    print(f"      → {ex}")

    print()


def check_contradictions(training_data):
    """Check for contradictory labels (e.g., TDI + benzín)"""

    print("="*70)
    print("🔍 Checking for Contradictions")
    print("="*70)
    print()

    contradictions = []

    for text, annotations in training_data:
        entities = annotations.get('entities', [])

        # Extract fuel labels
        fuel_entities = [text[start:end] for start, end, label in entities if label == 'FUEL']

        text_lower = text.lower()

        # Check for TDI indicators
        has_tdi = bool(re.search(r'\btdi\b', text_lower))
        has_td = bool(re.search(r'\btd[is]?\b', text_lower))

        # Check for diesel indicators
        has_diesel = any(f.lower() in ['diesel', 'nafta', 'tdi'] for f in fuel_entities)

        # Check for benzín indicators
        has_benzin = any(f.lower() in ['benzín', 'benzin', 'gas'] for f in fuel_entities)

        # TDI + benzín is contradictory
        if (has_tdi or has_td) and has_benzin:
            contradictions.append({
                'text': text[:100] + "...",
                'issue': f"TDI/TD engine but labeled as benzín: {fuel_entities}",
                'entities': fuel_entities
            })

        # Check for multiple different fuel types in same listing
        unique_fuels = set(f.lower() for f in fuel_entities)
        if len(unique_fuels) > 1:
            # Allow diesel/nafta/tdi as synonyms
            diesel_syns = {'diesel', 'nafta', 'tdi', 'td'}
            benzin_syns = {'benzín', 'benzin'}

            if not (unique_fuels.issubset(diesel_syns) or unique_fuels.issubset(benzin_syns)):
                contradictions.append({
                    'text': text[:100] + "...",
                    'issue': f"Multiple different fuel types: {fuel_entities}",
                    'entities': fuel_entities
                })

    if contradictions:
        print(f"❌ Found {len(contradictions)} contradictions:\n")
        for i, c in enumerate(contradictions, 1):
            print(f"{i}. {c['issue']}")
            print(f"   Text: {c['text']}")
            print(f"   Labeled as: {c['entities']}")
            print()
    else:
        print("✅ No contradictions found!")
        print()


def check_unit_consistency(training_data):
    """Check for inconsistent unit labeling"""

    print("="*70)
    print("🔍 Checking Unit Consistency")
    print("="*70)
    print()

    # Check mileage labels
    mileage_with_units = []
    mileage_without_units = []

    for text, annotations in training_data:
        entities = annotations.get('entities', [])

        for start, end, label in entities:
            if label == 'MILEAGE':
                value = text[start:end]
                if 'km' in value.lower():
                    mileage_with_units.append(value)
                else:
                    mileage_without_units.append(value)

    print("MILEAGE labels:")
    print(f"  With units (km):    {len(mileage_with_units)} examples")
    if mileage_with_units[:3]:
        print(f"    Examples: {', '.join(mileage_with_units[:3])}")

    print(f"  Without units:      {len(mileage_without_units)} examples")
    if mileage_without_units[:3]:
        print(f"    Examples: {', '.join(mileage_without_units[:3])}")

    if mileage_with_units and mileage_without_units:
        print("\n  ⚠️  Inconsistent! Some have units, some don't")
    else:
        print("\n  ✅ Consistent!")

    print()

    # Check power labels
    power_with_units = []
    power_without_units = []

    for text, annotations in training_data:
        entities = annotations.get('entities', [])

        for start, end, label in entities:
            if label == 'POWER':
                value = text[start:end]
                if 'kw' in value.lower():
                    power_with_units.append(value)
                else:
                    power_without_units.append(value)

    print("POWER labels:")
    print(f"  With units (kW):    {len(power_with_units)} examples")
    if power_with_units[:3]:
        print(f"    Examples: {', '.join(power_with_units[:3])}")

    print(f"  Without units:      {len(power_without_units)} examples")
    if power_without_units[:3]:
        print(f"    Examples: {', '.join(power_without_units[:3])}")

    if power_with_units and power_without_units:
        print("\n  ⚠️  Inconsistent! Some have units, some don't")
    else:
        print("\n  ✅ Consistent!")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 check_training_quality.py <training_data.json>")
        print("\nExample:")
        print("  python3 check_training_quality.py training_data_labeled.json")
        sys.exit(1)

    filename = sys.argv[1]

    print()
    print("="*70)
    print("📊 Training Data Quality Check")
    print("="*70)
    print(f"File: {filename}")
    print()

    try:
        training_data = load_training_data(filename)
        print(f"✓ Loaded {len(training_data)} examples\n")
    except FileNotFoundError:
        print(f"❌ Error: File '{filename}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        sys.exit(1)

    # Run checks
    check_fuel_consistency(training_data)
    check_contradictions(training_data)
    check_unit_consistency(training_data)

    print("="*70)
    print("📋 Recommendations")
    print("="*70)
    print()
    print("1. Normalize fuel types:")
    print("   - All diesel variants → 'diesel'")
    print("   - All benzín variants → 'benzín'")
    print()
    print("2. Fix contradictions:")
    print("   - Remove 'TDI + benzín' examples or fix the labels")
    print()
    print("3. Decide on units:")
    print("   - Either WITH units: '150000 km', '110 kW'")
    print("   - Or WITHOUT: '150000', '110'")
    print("   - Be consistent!")
    print()
    print("4. Re-label inconsistent data:")
    print("   - Use label_data_assisted.py to review and fix")
    print()
    print("5. Retrain model with clean data:")
    print("   - python3 -m ml.train_ml_model")
    print()
    print("Expected F1 improvement: 70% → 80%+ with clean labels")
    print("="*70)


if __name__ == "__main__":
    main()
