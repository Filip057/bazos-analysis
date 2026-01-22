"""
Deduplicate Manual Review Data
================================

Removes duplicate entries from manual_review_data.json based on unique car URLs.
Each offer should only appear once in the manual reviews.

Usage:
    python3 -m ml.deduplicate_manual_reviews
"""

import json
from pathlib import Path
from typing import Dict, List


def deduplicate_manual_reviews(
    review_file: str = 'manual_review_data.json',
    backup: bool = True
) -> Dict[str, int]:
    """
    Remove duplicates from manual review data based on car_id (URL).

    Args:
        review_file: Path to manual_review_data.json
        backup: If True, creates a backup before modifying

    Returns:
        Dict with statistics: original_count, unique_count, duplicates_removed
    """
    review_path = Path(review_file)

    if not review_path.exists():
        print(f"ℹ️  File not found: {review_file}")
        print("   This is normal if you haven't reviewed any disagreements yet.")
        return {'error': 'file_not_found'}

    # Load the reviews
    print(f"📂 Loading {review_file}...")
    with open(review_path, 'r', encoding='utf-8') as f:
        reviews = json.load(f)

    original_count = len(reviews)
    print(f"   Original entries: {original_count}")

    # Create backup if requested
    if backup:
        backup_path = review_path.with_suffix('.json.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        print(f"✓ Backup created: {backup_path}")

    # Deduplicate based on car_id (URL)
    # Keep the LATEST review for each car_id (most recent timestamp)
    print("\n🔍 Deduplicating based on car_id (URL)...")
    car_id_to_review = {}  # Maps car_id -> review (keeping the latest one)

    for review in reviews:
        car_id = review.get('car_id', '')

        if not car_id:
            # Keep items without car_id (shouldn't happen, but just in case)
            # Use a unique placeholder
            car_id = f"_unknown_{len(car_id_to_review)}"

        # If we've seen this car_id before, compare timestamps
        if car_id in car_id_to_review:
            existing_timestamp = car_id_to_review[car_id].get('timestamp', '')
            new_timestamp = review.get('timestamp', '')

            # Keep the review with the later timestamp
            if new_timestamp > existing_timestamp:
                car_id_to_review[car_id] = review
            # Otherwise keep the existing one
        else:
            # First occurrence
            car_id_to_review[car_id] = review

    unique_reviews = list(car_id_to_review.values())
    unique_count = len(unique_reviews)
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
        # Show some example duplicate car_ids
        duplicate_ids = [car_id for car_id, review in car_id_to_review.items()
                        if sum(1 for r in reviews if r.get('car_id') == car_id) > 1]

        if duplicate_ids:
            print(f"\n📋 Example duplicate car IDs (showing first 5):")
            for car_id in duplicate_ids[:5]:
                count = sum(1 for r in reviews if r.get('car_id') == car_id)
                print(f"   - {car_id} (appeared {count} times)")
            if len(duplicate_ids) > 5:
                print(f"   ... and {len(duplicate_ids) - 5} more")

        # Save deduplicated reviews
        print(f"\n💾 Saving deduplicated reviews to {review_file}...")
        with open(review_path, 'w', encoding='utf-8') as f:
            json.dump(unique_reviews, f, ensure_ascii=False, indent=2)

        print(f"✅ Done! Removed {duplicates_removed} duplicate entries.")
        print(f"   Kept the most recent review for each car.")
        print(f"\n💡 You can restore the original file from: {review_path.with_suffix('.json.backup')}")
    else:
        print("\n✅ No duplicates found! Manual reviews are already clean.")

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
    print("🧹 Manual Review Data Deduplication Tool")
    print("="*60)
    print()

    stats = deduplicate_manual_reviews(backup=backup)

    if 'error' not in stats:
        print("\n" + "="*60)
        print("✓ Deduplication complete!")
        print("="*60)


if __name__ == "__main__":
    main()
