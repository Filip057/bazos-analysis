"""
Filter Training Data - Keep Only Rich Examples
==============================================

This script filters out examples that don't have useful data.
Only keeps examples where regex found at least 2/3 fields.

This way you don't waste time labeling empty examples!

Usage:
    python3 filter_training_data.py --input training_data_scraped.json --output filtered_data.json
"""

import json
import argparse
import re

# Regex patterns (same as scraper)
MILEAGE_PATTERN_1 = re.compile(r'(\d{1,3}(?:\s?\d{3})*(?:\.\d+)?)\s?km', re.IGNORECASE)
MILEAGE_PATTERN_2 = re.compile(r'(\d{1,3}(?:\s?\d{3})*)(?:\.|\s?tis\.?)\s?km', re.IGNORECASE)
MILEAGE_PATTERN_3 = re.compile(r'(\d{1,3}(?:\s?\d{3})*)(?:\s?xxx\s?km)', re.IGNORECASE)
POWER_PATTERN = re.compile(r'(\d{1,3})\s?kw', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'(?:rok výroby|R\.?V\.?|rok|r\.?v\.?|výroba)?\s*(\d{4})\b', re.IGNORECASE)


def get_mileage(text: str) -> bool:
    """Check if mileage exists"""
    text = re.sub(r'[^\w\s]', '', text.lower())
    if MILEAGE_PATTERN_1.search(text) or MILEAGE_PATTERN_2.search(text) or MILEAGE_PATTERN_3.search(text):
        return True
    return False


def get_year(text: str) -> bool:
    """Check if year exists"""
    return YEAR_PATTERN.search(text) is not None


def get_power(text: str) -> bool:
    """Check if power exists"""
    text = re.sub(r'[^\w\s]', '', text.lower())
    return POWER_PATTERN.search(text) is not None


def analyze_example(text: str) -> dict:
    """Check what data an example has"""
    has_mileage = get_mileage(text)
    has_year = get_year(text)
    has_power = get_power(text)

    fields_found = sum([has_mileage, has_year, has_power])

    return {
        'mileage': has_mileage,
        'year': has_year,
        'power': has_power,
        'fields_found': fields_found
    }


def filter_training_data(input_file: str, output_file: str, min_fields: int = 2):
    """
    Filter training data to keep only rich examples.

    Args:
        input_file: Input JSON file from scraper
        min_fields: Minimum fields required (default: 2 out of 3)
    """
    print(f"\n{'='*60}")
    print(f"Filtering Training Data")
    print(f"{'='*60}")
    print(f"Input: {input_file}")
    print(f"Minimum fields required: {min_fields}/3")
    print(f"{'='*60}\n")

    # Load scraped data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total examples in file: {len(data)}")

    # Analyze each example
    filtered = []
    stats = {0: 0, 1: 0, 2: 0, 3: 0}

    for item in data:
        text = item['text']
        analysis = analyze_example(text)
        fields_found = analysis['fields_found']

        stats[fields_found] += 1

        # Keep if has enough fields
        if fields_found >= min_fields:
            filtered.append(item)

    # Show statistics
    print(f"\n📊 Data Quality Analysis:")
    print(f"{'='*60}")
    print(f"Examples with 3/3 fields: {stats[3]:4d} ({stats[3]/len(data)*100:.1f}%) ⭐⭐⭐")
    print(f"Examples with 2/3 fields: {stats[2]:4d} ({stats[2]/len(data)*100:.1f}%) ⭐⭐")
    print(f"Examples with 1/3 fields: {stats[1]:4d} ({stats[1]/len(data)*100:.1f}%) ⭐")
    print(f"Examples with 0/3 fields: {stats[0]:4d} ({stats[0]/len(data)*100:.1f}%) ❌")
    print(f"{'='*60}")
    print(f"\nFiltered: {len(filtered)} examples kept (with {min_fields}+ fields)")
    print(f"Removed:  {len(data) - len(filtered)} examples (too sparse)")
    print(f"{'='*60}\n")

    if len(filtered) < 50:
        print(f"⚠️  Warning: Only {len(filtered)} good examples found!")
        print(f"   You might need to scrape more data or lower min_fields to {min_fields-1}\n")

    # Save filtered data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    # Save texts for labeling
    text_file = output_file.replace('.json', '_texts.txt')
    with open(text_file, 'w', encoding='utf-8') as f:
        for item in filtered:
            f.write(item['text'] + '\n')

    print(f"✓ Saved filtered data to: {output_file}")
    print(f"✓ Saved texts to: {text_file}")

    # Show sample of kept examples
    print(f"\n📝 Sample of filtered examples (first 3):\n")
    for i, item in enumerate(filtered[:3], 1):
        analysis = analyze_example(item['text'])
        print(f"{i}. Fields: {analysis['fields_found']}/3")
        print(f"   Has: ", end="")
        if analysis['mileage']: print("✓ Mileage ", end="")
        if analysis['year']: print("✓ Year ", end="")
        if analysis['power']: print("✓ Power", end="")
        print(f"\n   Text: {item['text'][:80]}...\n")

    print(f"\n🎯 Next step:")
    print(f"   python3 label_data.py --input {text_file} --output training_data_labeled.json --limit 50")
    print()

    return len(filtered)


def main():
    parser = argparse.ArgumentParser(
        description="Filter training data to keep only rich examples"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file from scraper (e.g., training_data_scraped.json)"
    )
    parser.add_argument(
        "--output",
        default="filtered_training_data.json",
        help="Output JSON file with filtered data"
    )
    parser.add_argument(
        "--min-fields",
        type=int,
        default=2,
        choices=[1, 2, 3],
        help="Minimum fields required (1, 2, or 3). Default: 2"
    )

    args = parser.parse_args()

    filtered_count = filter_training_data(args.input, args.output, args.min_fields)

    if filtered_count >= 50:
        print(f"✅ Great! You have {filtered_count} rich examples.")
        print(f"   Label 50-100 of these and you'll have a good model!\n")
    elif filtered_count >= 30:
        print(f"⚠️  You have {filtered_count} rich examples.")
        print(f"   Label all of them, but consider scraping more data.\n")
    else:
        print(f"❌ Only {filtered_count} rich examples found.")
        print(f"   Options:")
        print(f"   1. Lower threshold: --min-fields 1")
        print(f"   2. Scrape more data with different brands\n")


if __name__ == "__main__":
    main()
