"""
Deduplicate Review Queue
=========================

Removes duplicate entries from review_queue.json based on unique car URLs.
Each offer should only appear once in the review queue.

Usage:
    python3 -m ml.deduplicate_review_queue
"""

import json
from pathlib import Path
from typing import Dict, List


def deduplicate_review_queue(
    queue_file: str = 'review_queue.json',
    backup: bool = True
) -> Dict[str, int]:
    """
    Remove duplicates from review queue based on car_id (URL).

    Args:
        queue_file: Path to review_queue.json
        backup: If True, creates a backup before modifying

    Returns:
        Dict with statistics: original_count, unique_count, duplicates_removed
    """
    queue_path = Path(queue_file)

    if not queue_path.exists():
        print(f"❌ File not found: {queue_file}")
        print("   Make sure you run this from the project root directory.")
        return {'error': 'file_not_found'}

    # Load the queue
    print(f"📂 Loading {queue_file}...")
    with open(queue_path, 'r', encoding='utf-8') as f:
        queue = json.load(f)

    original_count = len(queue)
    print(f"   Original entries: {original_count}")

    # Create backup if requested
    if backup:
        backup_path = queue_path.with_suffix('.json.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        print(f"✓ Backup created: {backup_path}")

    # Deduplicate based on car_id (URL)
    print("\n🔍 Deduplicating based on car_id (URL)...")
    seen_urls = set()
    unique_queue = []
    duplicate_urls = []

    for item in queue:
        car_id = item.get('car_id', '')

        if not car_id:
            # Keep items without car_id (shouldn't happen, but just in case)
            unique_queue.append(item)
            continue

        if car_id not in seen_urls:
            # First occurrence - keep it
            seen_urls.add(car_id)
            unique_queue.append(item)
        else:
            # Duplicate - skip it
            duplicate_urls.append(car_id)

    unique_count = len(unique_queue)
    duplicates_removed = original_count - unique_count

    # Show statistics
    print(f"\n{'='*60}")
    print(f"📊 Deduplication Statistics")
    print(f"{'='*60}")
    print(f"Original entries:      {original_count}")
    print(f"Unique entries:        {unique_count}")
    print(f"Duplicates removed:    {duplicates_removed}")
    print(f"{'='*60}")

    if duplicates_removed > 0:
        # Show some example duplicate URLs
        print(f"\n📋 Example duplicate URLs (showing first 5):")
        for url in duplicate_urls[:5]:
            print(f"   - {url}")
        if len(duplicate_urls) > 5:
            print(f"   ... and {len(duplicate_urls) - 5} more")

        # Save deduplicated queue
        print(f"\n💾 Saving deduplicated queue to {queue_file}...")
        with open(queue_path, 'w', encoding='utf-8') as f:
            json.dump(unique_queue, f, ensure_ascii=False, indent=2)

        print(f"✅ Done! Removed {duplicates_removed} duplicate entries.")
        print(f"\n💡 You can restore the original file from: {queue_path.with_suffix('.json.backup')}")
    else:
        print("\n✅ No duplicates found! Queue is already clean.")

    return {
        'original_count': original_count,
        'unique_count': unique_count,
        'duplicates_removed': duplicates_removed
    }


def main():
    """CLI entry point"""
    import sys

    # Check for --no-backup flag
    backup = "--no-backup" not in sys.argv

    print("="*60)
    print("🧹 Review Queue Deduplication Tool")
    print("="*60)
    print()

    stats = deduplicate_review_queue(backup=backup)

    if 'error' not in stats:
        print("\n" + "="*60)
        print("✓ Deduplication complete!")
        print("="*60)


if __name__ == "__main__":
    main()
