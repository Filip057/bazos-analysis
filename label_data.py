"""
Interactive Data Labeling Tool
==============================

This tool helps you create training data for the ML model.
It's educational and shows you how to prepare data for machine learning.

Usage:
    python label_data.py --input descriptions.txt --output training_data.json
"""

import json
import argparse
from typing import List, Dict, Tuple
from pathlib import Path


class DataLabeler:
    """Interactive tool for labeling car descriptions"""

    def __init__(self):
        self.labeled_data = []

    def highlight_text(self, text: str, start: int, end: int) -> str:
        """Add visual highlighting to show what was labeled"""
        return (
            text[:start] +
            f"\033[92m{text[start:end]}\033[0m" +  # Green text
            text[end:]
        )

    def label_single_text(self, text: str) -> Tuple[str, Dict]:
        """
        Label a single car description.

        Returns:
            (text, {"entities": [(start, end, label), ...]})
        """
        print("\n" + "=" * 80)
        print(f"Text: {text}")
        print("=" * 80)

        entities = []

        # Label MILEAGE
        print("\n📏 MILEAGE - Find the kilometers (e.g., '120000 km', '85 tis km')")
        mileage_text = input("  Type the mileage text (or press Enter to skip): ").strip()
        if mileage_text and mileage_text in text:
            start = text.find(mileage_text)
            end = start + len(mileage_text)
            entities.append((start, end, "MILEAGE"))
            print(f"  ✓ Labeled: {self.highlight_text(text, start, end)}")

        # Label YEAR
        print("\n📅 YEAR - Find the year of manufacture (e.g., '2015', 'rok 2018')")
        year_text = input("  Type the year text (or press Enter to skip): ").strip()
        if year_text and year_text in text:
            start = text.find(year_text)
            end = start + len(year_text)
            entities.append((start, end, "YEAR"))
            print(f"  ✓ Labeled: {self.highlight_text(text, start, end)}")

        # Label POWER
        print("\n⚡ POWER - Find the engine power (e.g., '110 kW', '150kW')")
        power_text = input("  Type the power text (or press Enter to skip): ").strip()
        if power_text and power_text in text:
            start = text.find(power_text)
            end = start + len(power_text)
            entities.append((start, end, "POWER"))
            print(f"  ✓ Labeled: {self.highlight_text(text, start, end)}")

        # Label FUEL (optional)
        print("\n⛽ FUEL - Find fuel type (e.g., 'benzín', 'nafta', 'diesel')")
        fuel_text = input("  Type the fuel text (or press Enter to skip): ").strip()
        if fuel_text and fuel_text in text:
            start = text.find(fuel_text)
            end = start + len(fuel_text)
            entities.append((start, end, "FUEL"))
            print(f"  ✓ Labeled: {self.highlight_text(text, start, end)}")

        print(f"\n✓ Labeled {len(entities)} entities")

        return text, {"entities": entities}

    def label_from_file(self, input_file: str, output_file: str, limit: int = None):
        """
        Label multiple texts from a file.

        Args:
            input_file: Text file with one description per line
            output_file: JSON file to save labeled data
            limit: Maximum number of texts to label
        """
        # Read input texts
        with open(input_file, 'r', encoding='utf-8') as f:
            texts = [line.strip() for line in f if line.strip()]

        if limit:
            texts = texts[:limit]

        print(f"\n🎓 Welcome to the ML Data Labeling Tool!")
        print(f"You'll label {len(texts)} car descriptions.")
        print(f"This creates training data for your machine learning model.\n")
        input("Press Enter to start...")

        labeled = []
        for i, text in enumerate(texts, 1):
            print(f"\n[{i}/{len(texts)}]")

            try:
                labeled_example = self.label_single_text(text)
                labeled.append(labeled_example)

                # Save progress after each one
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(labeled, f, ensure_ascii=False, indent=2)

                print(f"\n✓ Progress saved to {output_file}")

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted! Progress has been saved.")
                break

        print(f"\n\n🎉 Done! Labeled {len(labeled)} examples.")
        print(f"📁 Saved to: {output_file}")
        print(f"\n💡 Tip: You need at least 50-100 examples for a good model.")
        print(f"    You have {len(labeled)} so far.")

    def load_and_continue(self, output_file: str, input_file: str, limit: int = None):
        """Continue labeling from where you left off"""
        # Load existing labeled data
        if Path(output_file).exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                self.labeled_data = json.load(f)
            print(f"✓ Loaded {len(self.labeled_data)} previously labeled examples")

        # Get texts that aren't labeled yet
        with open(input_file, 'r', encoding='utf-8') as f:
            all_texts = [line.strip() for line in f if line.strip()]

        labeled_texts = {text for text, _ in self.labeled_data}
        remaining_texts = [t for t in all_texts if t not in labeled_texts]

        if limit:
            remaining_texts = remaining_texts[:limit]

        print(f"📊 Status: {len(self.labeled_data)} labeled, {len(remaining_texts)} remaining")

        if not remaining_texts:
            print("✓ All texts are labeled!")
            return

        # Continue labeling
        for i, text in enumerate(remaining_texts, len(self.labeled_data) + 1):
            print(f"\n[{i}/{len(self.labeled_data) + len(remaining_texts)}]")

            try:
                labeled_example = self.label_single_text(text)
                self.labeled_data.append(labeled_example)

                # Save progress
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.labeled_data, f, ensure_ascii=False, indent=2)

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted! Progress has been saved.")
                break


def main():
    parser = argparse.ArgumentParser(
        description="Label car descriptions for ML training"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input file with car descriptions (one per line)"
    )
    parser.add_argument(
        "--output",
        default="training_data.json",
        help="Output JSON file for labeled data"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of texts to label in this session"
    )
    parser.add_argument(
        "--continue",
        dest="continue_labeling",
        action="store_true",
        help="Continue from previously labeled data"
    )

    args = parser.parse_args()

    labeler = DataLabeler()

    if args.continue_labeling:
        labeler.load_and_continue(args.output, args.input, args.limit)
    else:
        labeler.label_from_file(args.input, args.output, args.limit)


if __name__ == "__main__":
    main()
