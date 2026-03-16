#!/usr/bin/env python3
"""
Quick check for misaligned entities - shows first 10 problems

Usage:
    python3 scripts/quick_check_alignment.py temp_combined_training.json
"""
import json
import sys


def check_alignment(data, max_show=10):
    """Quick alignment check"""
    print(f"🔍 Checking {len(data)} examples for misaligned entities...\n")

    total_entities = 0
    misaligned = 0
    shown = 0

    for idx, item in enumerate(data):
        # Parse format
        if isinstance(item, list) and len(item) == 2:
            text, annotations = item
            entities = annotations.get('entities', [])
        elif isinstance(item, dict):
            text = item.get('text', '')
            entities = item.get('entities', [])
        else:
            continue

        # Check each entity
        for ent in entities:
            total_entities += 1

            if len(ent) != 3:
                continue

            start, end, label = ent

            # Validate
            if start < 0 or end > len(text) or start >= end:
                misaligned += 1

                if shown < max_show:
                    print(f"❌ Example {idx} - {label}")
                    print(f"   Position: [{start}, {end}]")
                    print(f"   Problem: Invalid bounds")
                    print(f"   Text: {text[:100]}...")
                    print()
                    shown += 1

                continue

            extracted = text[start:end]

            # Check if empty
            if not extracted.strip():
                misaligned += 1

                if shown < max_show:
                    print(f"❌ Example {idx} - {label}")
                    print(f"   Position: [{start}, {end}]")
                    print(f"   Extracted: '{extracted}'")
                    print(f"   Problem: Empty entity")
                    print(f"   Context: ...{text[max(0, start-20):end+20]}...")
                    print()
                    shown += 1

    # Summary
    print("=" * 70)
    print(f"SUMMARY:")
    print(f"  Total entities:      {total_entities}")
    print(f"  Misaligned:          {misaligned} ({misaligned/total_entities*100:.1f}%)")
    print(f"  Valid:               {total_entities - misaligned} ({(total_entities-misaligned)/total_entities*100:.1f}%)")
    print("=" * 70)

    if misaligned > 0:
        loss_pct = misaligned / total_entities * 100
        print()
        if loss_pct > 10:
            print(f"❌ CRITICAL: {loss_pct:.1f}% data loss!")
            print(f"   Run: python3 scripts/validate_training_data.py --input {sys.argv[1]} --output fixed.json --fix")
        elif loss_pct > 5:
            print(f"⚠️  WARNING: {loss_pct:.1f}% data loss")
            print(f"   Consider fixing: python3 scripts/validate_training_data.py --input {sys.argv[1]} --fix")
        else:
            print(f"✅ Acceptable: {loss_pct:.1f}% data loss (< 5%)")
    else:
        print("\n✅ Perfect! No misaligned entities found!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/quick_check_alignment.py <training_data.json>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)

    check_alignment(data)
