"""
Check Labeling Progress
========================

Shows how many examples you've labeled vs how many are left.

Usage:
    python3 check_labeling_status.py --filtered filtered_training_v2.json --labeled training_data_labeled.json
"""

import json
import argparse


def check_status(filtered_file: str, labeled_file: str):
    """Check labeling progress"""

    # Load filtered data (all available examples)
    try:
        with open(filtered_file, 'r', encoding='utf-8') as f:
            filtered_data = json.load(f)
            total_available = len(filtered_data)
            all_texts = [item['text'] for item in filtered_data]
    except FileNotFoundError:
        print(f"❌ Error: File '{filtered_file}' not found")
        return

    # Load labeled data (what you've already done)
    try:
        with open(labeled_file, 'r', encoding='utf-8') as f:
            labeled_data = json.load(f)
            total_labeled = len(labeled_data)
            labeled_texts = {text for text, _ in labeled_data}
    except FileNotFoundError:
        print(f"⚠️  No labeled data file found yet")
        total_labeled = 0
        labeled_texts = set()

    # Calculate remaining
    remaining = total_available - total_labeled
    progress_pct = (total_labeled / total_available * 100) if total_available > 0 else 0

    # Display status
    print(f"\n{'='*60}")
    print(f"📊 Labeling Progress")
    print(f"{'='*60}")
    print(f"Filtered data:     {total_available} examples available")
    print(f"Already labeled:   {total_labeled} examples ({progress_pct:.1f}%)")
    print(f"Remaining:         {remaining} examples")
    print(f"{'='*60}\n")

    # Recommendation
    if remaining == 0:
        print(f"✅ All examples from {filtered_file} are labeled!")
        print(f"\n💡 Options:")
        print(f"   1. Train with current data: python3 train_ml_model.py --data {labeled_file}")
        print(f"   2. Scrape more data for better model:")
        print(f"      python3 scrape_mixed_brands.py --brands audi:20 bmw:20 mazda:20 --output training_new.json")
        print(f"      python3 filter_training_data.py --input training_new.json --output filtered_new.json")
        print(f"      python3 label_data_assisted.py --input filtered_new.json --output {labeled_file} --continue --limit 50")
    elif remaining < 25:
        print(f"⚠️  Only {remaining} examples left")
        print(f"\n💡 Recommendations:")
        print(f"   1. Label remaining {remaining} examples:")
        print(f"      python3 label_data_assisted.py --input {filtered_file} --output {labeled_file} --continue")
        print(f"   2. Then scrape more diverse data if you want 100+ total examples")
    else:
        print(f"✅ You have {remaining} examples left to label!")
        print(f"\n💡 Next step:")
        print(f"   python3 label_data_assisted.py --input {filtered_file} --output {labeled_file} --continue --limit 50")

    print()


def main():
    parser = argparse.ArgumentParser(description="Check labeling progress")
    parser.add_argument(
        "--filtered",
        default="filtered_training_v2.json",
        help="Filtered data file (all available examples)"
    )
    parser.add_argument(
        "--labeled",
        default="training_data_labeled.json",
        help="Labeled data file (already labeled)"
    )

    args = parser.parse_args()
    check_status(args.filtered, args.labeled)


if __name__ == "__main__":
    main()
