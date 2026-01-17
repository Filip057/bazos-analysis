"""
Check Label Consistency
========================

Analyzes labeled data for inconsistencies in formatting.

Usage:
    python3 check_label_consistency.py training_data_labeled.json
"""

import json
import sys
import re
from collections import Counter


def analyze_label_patterns(file_path: str):
    """Analyze consistency of labels"""

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Track patterns
    mileage_patterns = []
    power_patterns = []
    year_patterns = []
    fuel_patterns = []

    for item in data:
        if isinstance(item, (list, tuple)):
            text, annotations = item
            entities = annotations.get('entities', [])
        else:
            text = item.get('text', '')
            entities = item.get('entities', [])

        for start, end, label in entities:
            entity_text = text[start:end]

            if label == 'MILEAGE':
                mileage_patterns.append(entity_text)
            elif label == 'POWER':
                power_patterns.append(entity_text)
            elif label == 'YEAR':
                year_patterns.append(entity_text)
            elif label == 'FUEL':
                fuel_patterns.append(entity_text)

    # Analyze patterns
    print(f"\n{'='*60}")
    print(f"Label Consistency Analysis")
    print(f"{'='*60}\n")

    # MILEAGE analysis
    print(f"🚗 MILEAGE Patterns ({len(mileage_patterns)} total):")
    print(f"{'='*60}")

    # Check spacing
    with_space = sum(1 for m in mileage_patterns if ' km' in m)
    without_space = sum(1 for m in mileage_patterns if 'km' in m and ' km' not in m)
    has_t = sum(1 for m in mileage_patterns if 't' in m.lower() and 'km' in m)
    has_tis = sum(1 for m in mileage_patterns if 'tis' in m.lower())

    print(f"  With space ('200 000 km'):     {with_space}")
    print(f"  Without space ('200000km'):    {without_space}")
    print(f"  Using 't' abbreviation ('180tkm'): {has_t}")
    print(f"  Using 'tis' ('200 tis km'):    {has_tis}")

    # Show variety
    pattern_counter = Counter(mileage_patterns)
    if len(pattern_counter) > 20:
        print(f"\n  ⚠️  WARNING: {len(pattern_counter)} different formats found!")
        print(f"  Most common:")
        for pattern, count in pattern_counter.most_common(10):
            print(f"    '{pattern}': {count} times")
    print()

    # POWER analysis
    print(f"⚡ POWER Patterns ({len(power_patterns)} total):")
    print(f"{'='*60}")

    with_space = sum(1 for p in power_patterns if ' kw' in p.lower() or ' ps' in p.lower())
    without_space = sum(1 for p in power_patterns if 'kw' in p.lower() and ' kw' not in p.lower())
    lowercase = sum(1 for p in power_patterns if 'kw' in p and 'kW' not in p)
    uppercase = sum(1 for p in power_patterns if 'kW' in p)
    has_period = sum(1 for p in power_patterns if p.endswith('.'))

    print(f"  With space ('110 kW'):         {with_space}")
    print(f"  Without space ('110kW'):       {without_space}")
    print(f"  Lowercase ('110kw'):           {lowercase}")
    print(f"  Uppercase ('110kW'):           {uppercase}")
    print(f"  With period ('110kw.'):        {has_period}")

    pattern_counter = Counter(power_patterns)
    if len(pattern_counter) > 20:
        print(f"\n  ⚠️  WARNING: {len(pattern_counter)} different formats!")
        print(f"  Most common:")
        for pattern, count in pattern_counter.most_common(10):
            print(f"    '{pattern}': {count} times")
    print()

    # YEAR analysis
    print(f"📅 YEAR Patterns ({len(year_patterns)} total):")
    print(f"{'='*60}")

    just_number = sum(1 for y in year_patterns if re.match(r'^\d{4}$', y))
    with_context = sum(1 for y in year_patterns if not re.match(r'^\d{4}$', y))

    print(f"  Just number ('2016'):          {just_number}")
    print(f"  With context ('rok 2016'):     {with_context}")

    if with_context > 0:
        print(f"\n  ⚠️  WARNING: Some years include context words!")
        print(f"  Examples with context:")
        context_examples = [y for y in year_patterns if not re.match(r'^\d{4}$', y)][:5]
        for ex in context_examples:
            print(f"    '{ex}'")
    print()

    # FUEL analysis
    print(f"⛽ FUEL Patterns ({len(fuel_patterns)} total):")
    print(f"{'='*60}")

    lowercase_fuel = sum(1 for f in fuel_patterns if f.islower())
    uppercase_fuel = sum(1 for f in fuel_patterns if f.isupper())
    mixed_fuel = sum(1 for f in fuel_patterns if not f.islower() and not f.isupper())

    print(f"  Lowercase ('diesel'):          {lowercase_fuel}")
    print(f"  Uppercase ('TDI'):             {uppercase_fuel}")
    print(f"  Mixed case ('Diesel'):         {mixed_fuel}")

    # Check for inflected forms (Czech adjectives)
    adjectives = sum(1 for f in fuel_patterns if f.endswith('ým') or f.endswith('ou'))
    if adjectives > 0:
        print(f"\n  ⚠️  WARNING: {adjectives} labels use adjective forms (ending with 'ým' or 'ou')!")
        adj_examples = [f for f in fuel_patterns if f.endswith('ým') or f.endswith('ou')][:5]
        print(f"  Examples:")
        for ex in adj_examples:
            print(f"    '{ex}' (should be base form)")

    pattern_counter = Counter(fuel_patterns)
    print(f"\n  Unique fuel variations: {len(pattern_counter)}")
    print(f"  Distribution:")
    for pattern, count in pattern_counter.most_common():
        print(f"    '{pattern}': {count} times")
    print()

    # Overall assessment
    print(f"{'='*60}")
    print(f"🎯 Consistency Score:")
    print(f"{'='*60}")

    issues = []

    if without_space > with_space * 0.2:  # More than 20% without space
        issues.append("❌ MILEAGE: Inconsistent spacing")

    if has_t > 10 or has_tis > 10:
        issues.append("⚠️  MILEAGE: Mixed abbreviations (t, tis, full numbers)")

    if abs(lowercase - uppercase) > len(power_patterns) * 0.2:
        issues.append("❌ POWER: Inconsistent case (kw vs kW)")

    if has_period > 0:
        issues.append("⚠️  POWER: Some labels include punctuation")

    if with_context > 0:
        issues.append("❌ YEAR: Some include context words ('rok 2016' instead of '2016')")

    if adjectives > 0:
        issues.append("❌ FUEL: Using adjective forms instead of base words")

    if len(Counter(fuel_patterns)) > 10:
        issues.append("⚠️  FUEL: Too many variations")

    if len(issues) == 0:
        print(f"✅ Labels are CONSISTENT!")
        print(f"   Ready for training.\n")
    else:
        print(f"❌ Found {len(issues)} consistency problems:\n")
        for issue in issues:
            print(f"   {issue}")
        print(f"\n{'='*60}")
        print(f"💡 Recommendations:")
        print(f"{'='*60}")
        print(f"1. Normalize your labels programmatically (I can create a script)")
        print(f"2. OR start fresh with consistent labeling")
        print(f"\nWith inconsistent data, your model will have low F1 score (<70%).")
        print(f"With consistent data, you should get F1 = 80-85%.\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 check_label_consistency.py <labeled_data.json>")
        sys.exit(1)

    analyze_label_patterns(sys.argv[1])
