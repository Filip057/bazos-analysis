"""
Deep Check for Entity Issues
=============================

This script performs a comprehensive check for entity issues:
1. Overlapping entities
2. Duplicate entities (same span, same or different label)
3. Invalid entity spans (out of bounds, negative, etc.)
4. Entity format issues
"""

import json
from pathlib import Path
from collections import defaultdict

def check_entities_deep(filepath: Path):
    """Deep check for all entity issues"""
    print(f"\n{'='*80}")
    print(f"Deep checking: {filepath}")
    print(f"{'='*80}")

    if not filepath.exists():
        print(f"⚠️  File not found")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    issues_found = []

    for idx, item in enumerate(data):
        # Handle different formats
        if isinstance(item, (list, tuple)):
            text, annotations = item
            entities = annotations.get('entities', [])
        elif isinstance(item, dict):
            if 'data' in item:
                text, annotations = item['data']
                entities = annotations.get('entities', [])
            else:
                text = item.get('text', '')
                entities = item.get('entities', [])
        else:
            continue

        if not entities:
            continue

        # Check for duplicates (exact same entity appears multiple times)
        entity_counts = defaultdict(int)
        for ent in entities:
            ent_tuple = tuple(ent)  # Convert list to tuple for hashing
            entity_counts[ent_tuple] += 1

        for ent, count in entity_counts.items():
            if count > 1:
                start, end, label = ent
                issues_found.append({
                    'index': idx,
                    'type': 'DUPLICATE',
                    'text': text[:100],
                    'entity': ent,
                    'count': count,
                    'entity_text': text[start:end] if start < len(text) and end <= len(text) else 'OUT_OF_BOUNDS'
                })

        # Check for same span with different labels
        span_labels = defaultdict(list)
        for ent in entities:
            start, end, label = ent[:3]  # Handle both list and tuple
            span = (start, end)
            span_labels[span].append(label)

        for span, labels in span_labels.items():
            if len(set(labels)) > 1:  # Multiple different labels for same span
                start, end = span
                issues_found.append({
                    'index': idx,
                    'type': 'SAME_SPAN_DIFFERENT_LABELS',
                    'text': text[:100],
                    'span': span,
                    'labels': labels,
                    'entity_text': text[start:end] if start < len(text) and end <= len(text) else 'OUT_OF_BOUNDS'
                })

        # Check for overlapping entities (partial overlap)
        for i, ent1 in enumerate(entities):
            start1, end1, label1 = ent1[:3]
            for j, ent2 in enumerate(entities):
                if i >= j:
                    continue
                start2, end2, label2 = ent2[:3]

                # Check for overlap
                if not (end1 <= start2 or end2 <= start1):
                    # They overlap
                    if not (start1 == start2 and end1 == end2):  # Not exact same span
                        issues_found.append({
                            'index': idx,
                            'type': 'OVERLAP',
                            'text': text[:100],
                            'entity1': (start1, end1, label1),
                            'entity2': (start2, end2, label2),
                            'text1': text[start1:end1] if start1 < len(text) and end1 <= len(text) else 'OUT_OF_BOUNDS',
                            'text2': text[start2:end2] if start2 < len(text) and end2 <= len(text) else 'OUT_OF_BOUNDS'
                        })

        # Check for invalid spans
        for ent in entities:
            start, end, label = ent[:3]
            if start < 0 or end < 0:
                issues_found.append({
                    'index': idx,
                    'type': 'NEGATIVE_SPAN',
                    'text': text[:100],
                    'entity': ent
                })
            elif start >= end:
                issues_found.append({
                    'index': idx,
                    'type': 'INVALID_SPAN_ORDER',
                    'text': text[:100],
                    'entity': ent
                })
            elif end > len(text):
                issues_found.append({
                    'index': idx,
                    'type': 'OUT_OF_BOUNDS',
                    'text': text[:100],
                    'entity': ent,
                    'text_len': len(text)
                })

    # Report findings
    if not issues_found:
        print(f"✅ No issues found!")
        return

    print(f"\n❌ Found {len(issues_found)} issues:\n")

    # Group by type
    by_type = defaultdict(list)
    for issue in issues_found:
        by_type[issue['type']].append(issue)

    for issue_type, issues in by_type.items():
        print(f"\n{issue_type}: {len(issues)} issues")
        print(f"{'-'*80}")
        for issue in issues[:10]:  # Show first 10 of each type
            print(f"\n  Example {issue['index']}:")
            print(f"    Text: {issue['text']}...")
            if issue_type == 'DUPLICATE':
                print(f"    Entity appears {issue['count']} times: {issue['entity']}")
                print(f"    Text: '{issue['entity_text']}'")
            elif issue_type == 'SAME_SPAN_DIFFERENT_LABELS':
                print(f"    Span {issue['span']} has multiple labels: {issue['labels']}")
                print(f"    Text: '{issue['entity_text']}'")
            elif issue_type == 'OVERLAP':
                print(f"    Entity 1: {issue['entity1']} = '{issue['text1']}'")
                print(f"    Entity 2: {issue['entity2']} = '{issue['text2']}'")
            else:
                print(f"    Entity: {issue.get('entity', 'N/A')}")

        if len(issues) > 10:
            print(f"\n  ... and {len(issues) - 10} more")

def main():
    files = [
        "training_data_labeled.json",
        "auto_training_data.json",
        "manual_review_data.json",
        "training_skoda.json",
        "filtered_training_skoda.json",
    ]

    for filename in files:
        filepath = Path(filename)
        if filepath.exists():
            check_entities_deep(filepath)

if __name__ == "__main__":
    main()
