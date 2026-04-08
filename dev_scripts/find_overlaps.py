"""
Script to find overlapping entities in training data
"""
import json
from pathlib import Path

def check_overlaps(entities):
    """Check if entities overlap"""
    overlaps = []
    duplicates = []

    for i, ent1 in enumerate(entities):
        for j, ent2 in enumerate(entities):
            if i >= j:
                continue
            start1, end1, label1 = ent1
            start2, end2, label2 = ent2

            # Check for exact duplicate spans with different labels
            if start1 == start2 and end1 == end2 and label1 != label2:
                duplicates.append((ent1, ent2))
            # Check if they overlap (share any tokens)
            elif not (end1 <= start2 or end2 <= start1):
                overlaps.append((ent1, ent2))

    return overlaps + duplicates

def scan_training_file(filepath):
    """Scan a training data file for overlaps"""
    print(f"\n{'='*80}")
    print(f"Scanning: {filepath}")
    print(f"{'='*80}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    problems_found = 0

    for idx, item in enumerate(data):
        # Handle different formats
        if isinstance(item, (list, tuple)):
            text, annotations = item
        elif isinstance(item, dict):
            if 'data' in item:
                # Auto/manual review format
                text, annotations = item['data']
            else:
                text = item.get('text', '')
                annotations = {'entities': item.get('entities', [])}
        else:
            continue

        entities = annotations.get('entities', [])

        if not entities:
            continue

        overlaps = check_overlaps(entities)

        if overlaps:
            problems_found += 1
            print(f"\n❌ OVERLAP FOUND at index {idx}:")
            print(f"   Text: {text[:100]}...")
            print(f"   Entities: {entities}")
            for ent1, ent2 in overlaps:
                print(f"   Conflict: {ent1} overlaps with {ent2}")
                start1, end1, label1 = ent1
                start2, end2, label2 = ent2
                print(f"   Text1 ({label1}): '{text[start1:end1]}'")
                print(f"   Text2 ({label2}): '{text[start2:end2]}'")

    if problems_found == 0:
        print(f"✅ No overlaps found in {filepath}")
    else:
        print(f"\n⚠️  Total problems found: {problems_found}")

    return problems_found

def main():
    files_to_check = [
        "training_data_labeled.json",
        "auto_training_data.json",
        "manual_review_data.json",
        "training_skoda.json",
        "filtered_training_skoda.json"
    ]

    total_problems = 0

    for filename in files_to_check:
        filepath = Path(filename)
        if filepath.exists():
            problems = scan_training_file(filepath)
            total_problems += problems
        else:
            print(f"\n⚠️  File not found: {filename}")

    print(f"\n{'='*80}")
    print(f"SUMMARY: Total overlapping entities found: {total_problems}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
