"""
Clean All Duplicates
=====================

Removes duplicates from both review_queue.json and manual_review_data.json.
This is a convenience script that runs both deduplication tools.

Usage:
    python3 -m ml.clean_all_duplicates
"""

from ml.deduplicate_review_queue import deduplicate_review_queue
from ml.deduplicate_manual_reviews import deduplicate_manual_reviews


def main():
    """Clean all duplicate entries from review files"""
    import sys

    # Check for --no-backup flag
    backup = "--no-backup" not in sys.argv

    print("="*60)
    print("🧹 Clean All Duplicates - Complete Cleanup Tool")
    print("="*60)
    print()

    total_removed = 0

    # Clean review queue
    print("\n" + "─"*60)
    print("1️⃣  Cleaning review_queue.json")
    print("─"*60)
    stats1 = deduplicate_review_queue(backup=backup)
    if 'duplicates_removed' in stats1:
        total_removed += stats1['duplicates_removed']

    # Clean manual reviews
    print("\n\n" + "─"*60)
    print("2️⃣  Cleaning manual_review_data.json")
    print("─"*60)
    stats2 = deduplicate_manual_reviews(backup=backup)
    if 'duplicates_removed' in stats2:
        total_removed += stats2['duplicates_removed']

    # Final summary
    print("\n\n" + "="*60)
    print("✅ CLEANUP COMPLETE!")
    print("="*60)
    print(f"Total duplicates removed: {total_removed}")

    if stats1.get('duplicates_removed', 0) > 0 or stats2.get('duplicates_removed', 0) > 0:
        print(f"\n💡 Backups created with .backup extension")
        print(f"   You can safely delete them once you verify everything works.")

    print("\n🎯 Next steps:")
    print("   1. Run: python3 -m ml.review_disagreements")
    print("   2. Your queue should now have the correct number of items!")
    print("="*60)


if __name__ == "__main__":
    main()
