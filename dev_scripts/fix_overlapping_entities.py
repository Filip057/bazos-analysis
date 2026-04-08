"""
Fix Overlapping Entities in Training Data
==========================================

This script detects and resolves overlapping entities in training data.
When entities overlap, it resolves them using these rules:
1. If entities are exactly the same span with different labels, keep the one with higher priority (MILEAGE > YEAR > POWER > FUEL)
2. If entities partially overlap, keep the longer/more specific one
3. Log all changes for review

Usage:
    python3 fix_overlapping_entities.py
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Entity priority (higher number = higher priority when resolving conflicts)
ENTITY_PRIORITY = {
    'MILEAGE': 4,
    'YEAR': 3,
    'POWER': 2,
    'FUEL': 1,
}


def entities_overlap(ent1: Tuple[int, int, str], ent2: Tuple[int, int, str]) -> bool:
    """Check if two entities overlap"""
    start1, end1, _ = ent1
    start2, end2, _ = ent2

    # They overlap if one starts before the other ends
    return not (end1 <= start2 or end2 <= start1)


def resolve_overlap(ent1: Tuple[int, int, str], ent2: Tuple[int, int, str]) -> Tuple[int, int, str]:
    """
    Resolve overlap between two entities by keeping the better one.

    Rules:
    1. If exact same span, keep higher priority entity
    2. If different spans, keep the longer one
    3. If same length, keep higher priority
    """
    start1, end1, label1 = ent1
    start2, end2, label2 = ent2

    # Exact same span - use priority
    if start1 == start2 and end1 == end2:
        if ENTITY_PRIORITY.get(label1, 0) >= ENTITY_PRIORITY.get(label2, 0):
            return ent1
        else:
            return ent2

    # Different spans - keep the longer one
    len1 = end1 - start1
    len2 = end2 - start2

    if len1 > len2:
        return ent1
    elif len2 > len1:
        return ent2
    else:
        # Same length - use priority
        if ENTITY_PRIORITY.get(label1, 0) >= ENTITY_PRIORITY.get(label2, 0):
            return ent1
        else:
            return ent2


def remove_overlaps(entities: List[Tuple[int, int, str]], text: str) -> Tuple[List[Tuple[int, int, str]], List[str]]:
    """
    Remove overlapping entities from a list.
    Returns cleaned entities and list of changes made.
    """
    if not entities or len(entities) <= 1:
        return entities, []

    # Sort by start position
    sorted_entities = sorted(entities, key=lambda x: (x[0], x[1]))

    cleaned = []
    changes = []
    i = 0

    while i < len(sorted_entities):
        current = sorted_entities[i]

        # Check for overlaps with remaining entities
        has_overlap = False
        j = i + 1

        while j < len(sorted_entities):
            next_entity = sorted_entities[j]

            if entities_overlap(current, next_entity):
                has_overlap = True
                # Resolve the overlap
                winner = resolve_overlap(current, next_entity)
                loser = next_entity if winner == current else current

                start_w, end_w, label_w = winner
                start_l, end_l, label_l = loser

                changes.append(
                    f"  Overlap at [{start_w}:{end_w}]: kept {label_w} '{text[start_w:end_w]}', "
                    f"removed {label_l} '{text[start_l:end_l]}'"
                )

                # Update current to winner, remove loser
                current = winner
                sorted_entities.pop(j)

                # Don't increment j, check the same position again
            else:
                # No overlap, check next
                j += 1

        cleaned.append(current)
        i += 1

    # Final pass: ensure no overlaps remain
    final_cleaned = []
    for ent in cleaned:
        # Check if it overlaps with any already added
        overlaps_with_existing = False
        for existing in final_cleaned:
            if entities_overlap(ent, existing):
                overlaps_with_existing = True
                break

        if not overlaps_with_existing:
            final_cleaned.append(ent)

    return final_cleaned, changes


def fix_training_file(filepath: Path) -> Tuple[int, int]:
    """
    Fix overlapping entities in a training file.
    Returns (total_examples, fixed_examples)
    """
    print(f"\n{'='*80}")
    print(f"Processing: {filepath}")
    print(f"{'='*80}")

    if not filepath.exists():
        print(f"⚠️  File not found, skipping")
        return 0, 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_examples = len(data)
    fixed_examples = 0
    all_changes = []

    for idx, item in enumerate(data):
        # Handle different formats
        if isinstance(item, (list, tuple)):
            text, annotations = item
            entities = annotations.get('entities', [])
        elif isinstance(item, dict):
            if 'data' in item:
                # Auto/manual review format
                text, annotations = item['data']
                entities = annotations.get('entities', [])
            else:
                text = item.get('text', '')
                entities = item.get('entities', [])
                annotations = {'entities': entities}
        else:
            continue

        if not entities or len(entities) <= 1:
            continue

        # Check for overlaps and fix
        cleaned_entities, changes = remove_overlaps(entities, text)

        if changes:
            fixed_examples += 1
            all_changes.append(f"\nExample {idx}:")
            all_changes.append(f"  Text: {text[:100]}...")
            all_changes.extend(changes)

            # Update the data structure
            if isinstance(item, (list, tuple)):
                data[idx] = (text, {'entities': cleaned_entities})
            elif 'data' in item:
                item['data'] = (text, {'entities': cleaned_entities})
            else:
                item['entities'] = cleaned_entities

    # Save fixed data
    if fixed_examples > 0:
        backup_path = filepath.with_suffix('.json.backup')
        print(f"\n📦 Creating backup: {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 Saving fixed data to: {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Fixed {fixed_examples} examples out of {total_examples}")
        print(f"\n📝 Changes made:")
        for change in all_changes[:50]:  # Limit output
            print(change)
        if len(all_changes) > 50:
            print(f"\n... and {len(all_changes) - 50} more changes")
    else:
        print(f"✅ No overlapping entities found in {total_examples} examples")

    return total_examples, fixed_examples


def main():
    """Fix overlapping entities in all training data files"""

    print(f"\n{'='*80}")
    print(f"🔧 Fixing Overlapping Entities in Training Data")
    print(f"{'='*80}\n")

    files_to_fix = [
        "training_data_labeled.json",
        "auto_training_data.json",
        "manual_review_data.json",
        "training_skoda.json",
        "filtered_training_skoda.json",
    ]

    total_files = 0
    total_examples = 0
    total_fixed = 0

    for filename in files_to_fix:
        filepath = Path(filename)
        if filepath.exists():
            total_files += 1
            examples, fixed = fix_training_file(filepath)
            total_examples += examples
            total_fixed += fixed

    print(f"\n{'='*80}")
    print(f"📊 SUMMARY")
    print(f"{'='*80}")
    print(f"Files processed:     {total_files}")
    print(f"Total examples:      {total_examples}")
    print(f"Examples fixed:      {total_fixed}")
    print(f"{'='*80}\n")

    if total_fixed > 0:
        print(f"✅ Successfully fixed {total_fixed} examples with overlapping entities!")
        print(f"   Backups saved with .backup extension")
        print(f"   You can now run retrain_model.py")
    else:
        print(f"✅ No overlapping entities found!")
        print(f"   Your training data is clean.")

    print()
    return 0 if total_fixed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
