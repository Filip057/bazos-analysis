"""
Assisted Data Labeling Tool
============================

MUCH FASTER labeling with regex pre-annotation!
- Regex auto-finds entities and suggests them
- You just press Enter to accept or type correction
- 5-10x faster than manual labeling

Usage:
    python3 label_data_assisted.py --input filtered_training_mixed.json --output training_data_labeled.json --limit 50
"""

import json
import argparse
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Import centralized regex patterns
from patterns import (
    MILEAGE_PATTERN_1,
    MILEAGE_PATTERN_2,
    MILEAGE_PATTERN_3,
    MILEAGE_PATTERN_4,
    MILEAGE_PATTERN_5,
    MILEAGE_PATTERN_6,
    POWER_PATTERN_1,
    POWER_PATTERN_2,
    POWER_PATTERN_3,
    YEAR_PATTERN,
    FUEL_PATTERN
)


class AssistedLabeler:
    """Fast labeling with regex assistance"""

    def __init__(self):
        self.labeled_data = []
        self.stats = {
            'auto_accepted': 0,
            'manually_corrected': 0,
            'manually_entered': 0,
            'skipped': 0
        }

    def highlight_text(self, text: str, start: int, end: int, color: str = '92') -> str:
        """Add visual highlighting"""
        return (
            text[:start] +
            f"\033[{color}m{text[start:end]}\033[0m" +
            text[end:]
        )

    def find_entity_in_text(self, text: str, entity_text: str) -> Optional[Tuple[int, int]]:
        """Find entity position in text"""
        # Try exact match first
        pos = text.find(entity_text)
        if pos != -1:
            return (pos, pos + len(entity_text))

        # Try case-insensitive
        pos = text.lower().find(entity_text.lower())
        if pos != -1:
            return (pos, pos + len(entity_text))

        return None

    def auto_find_mileage(self, text: str) -> List[Tuple[str, int, int]]:
        """Find all mileage mentions"""
        results = []

        # Try all mileage patterns
        patterns = [MILEAGE_PATTERN_1, MILEAGE_PATTERN_2, MILEAGE_PATTERN_3,
                   MILEAGE_PATTERN_4, MILEAGE_PATTERN_5, MILEAGE_PATTERN_6]

        for pattern in patterns:
            for match in pattern.finditer(text):
                full_match = match.group(0)
                start = match.start()
                end = match.end()
                results.append((full_match, start, end))

        # Deduplicate overlapping matches (keep longest match at same position)
        seen_positions = {}
        for match_text, start, end in results:
            if start not in seen_positions or len(match_text) > len(seen_positions[start][0]):
                seen_positions[start] = (match_text, start, end)

        results = sorted(seen_positions.values(), key=lambda x: x[1])
        return results

    def auto_find_year(self, text: str) -> List[Tuple[str, int, int]]:
        """Find all year mentions (returns just the 4-digit year)"""
        results = []

        for match in YEAR_PATTERN.finditer(text):
            year_str = match.group(0)  # Just the year like "2016"
            year = int(year_str)

            # Only valid car years
            if 1990 <= year <= 2030:
                start = match.start()
                end = match.end()
                results.append((year_str, start, end))

        return list(set(results))

    def auto_find_power(self, text: str) -> List[Tuple[str, int, int]]:
        """Find all power mentions (returns value + unit like '110 kW')"""
        results = []

        # Try all power patterns
        patterns = [POWER_PATTERN_1, POWER_PATTERN_2, POWER_PATTERN_3]

        for pattern in patterns:
            for match in pattern.finditer(text):
                full_match = match.group(0)
                start = match.start()
                end = match.end()
                results.append((full_match, start, end))

        # Deduplicate overlapping matches
        seen_positions = {}
        for match_text, start, end in results:
            if start not in seen_positions or len(match_text) > len(seen_positions[start][0]):
                seen_positions[start] = (match_text, start, end)

        results = sorted(seen_positions.values(), key=lambda x: x[1])
        return results

    def auto_find_fuel(self, text: str) -> List[Tuple[str, int, int]]:
        """Find all fuel mentions"""
        results = []

        for match in FUEL_PATTERN.finditer(text):
            full_match = match.group(0)
            start = match.start()
            end = match.end()
            results.append((full_match, start, end))

        return list(set(results))

    def label_entity_assisted(self, text: str, entity_name: str, emoji: str,
                            auto_finds: List[Tuple[str, int, int]]) -> Optional[Tuple[int, int, str]]:
        """Label single entity with assistance"""

        print(f"\n{emoji} {entity_name}")

        if not auto_finds:
            # No suggestion
            print(f"  No suggestion found")
            user_input = input(f"  Type the {entity_name.lower()} text, or press ENTER to skip: ").strip()

            if not user_input:
                self.stats['skipped'] += 1
                return None

            pos = self.find_entity_in_text(text, user_input)
            if pos:
                self.stats['manually_entered'] += 1
                return (pos[0], pos[1], entity_name.upper())
            else:
                print(f"  ⚠️  Warning: '{user_input}' not found in text")
                return None

        elif len(auto_finds) == 1:
            # Single suggestion
            suggestion, start, end = auto_finds[0]
            highlighted = self.highlight_text(text, start, end, '92')  # Green

            print(f"  Found: '{suggestion}'")
            print(f"  Context: ...{highlighted[max(0,start-30):min(len(text),end+30)]}...")

            user_input = input(f"  Press ENTER to accept, type 's' to skip, or type correct text: ").strip()

            if not user_input:
                # Accept suggestion
                self.stats['auto_accepted'] += 1
                return (start, end, entity_name.upper())
            elif user_input.lower() == 's' or user_input.lower() == 'skip':
                # Skip
                self.stats['skipped'] += 1
                return None
            else:
                # Manual correction
                pos = self.find_entity_in_text(text, user_input)
                if pos:
                    self.stats['manually_corrected'] += 1
                    return (pos[0], pos[1], entity_name.upper())
                else:
                    print(f"  ⚠️  Warning: '{user_input}' not found in text")
                    return None

        else:
            # Multiple suggestions
            print(f"  Multiple found:")
            for i, (suggestion, start, end) in enumerate(auto_finds, 1):
                context_start = max(0, start - 20)
                context_end = min(len(text), end + 20)
                context = text[context_start:end] + "..." if end < len(text) else text[context_start:end]
                print(f"    {i}. '{suggestion}' (...{context})")

            user_input = input(f"  Pick number (1-{len(auto_finds)}), type 's' to skip, or type correct text: ").strip()

            if not user_input or user_input.lower() == 's' or user_input.lower() == 'skip':
                self.stats['skipped'] += 1
                return None
            elif user_input.isdigit() and 1 <= int(user_input) <= len(auto_finds):
                # Pick from suggestions
                idx = int(user_input) - 1
                suggestion, start, end = auto_finds[idx]
                self.stats['auto_accepted'] += 1
                return (start, end, entity_name.upper())
            else:
                # Manual entry
                pos = self.find_entity_in_text(text, user_input)
                if pos:
                    self.stats['manually_entered'] += 1
                    return (pos[0], pos[1], entity_name.upper())
                else:
                    print(f"  ⚠️  Warning: '{user_input}' not found in text")
                    return None

    def label_single_text(self, text: str) -> Tuple[str, Dict]:
        """Label one text with assistance"""

        print(f"\n{'='*80}")
        print(f"📝 Text (first 500 chars):")
        print(f"{text[:500]}{'...' if len(text) > 500 else ''}")
        print(f"{'='*80}")

        entities = []

        # MILEAGE
        mileage_finds = self.auto_find_mileage(text)
        result = self.label_entity_assisted(text, "MILEAGE", "🚗", mileage_finds)
        if result:
            entities.append(result)

        # YEAR
        year_finds = self.auto_find_year(text)
        result = self.label_entity_assisted(text, "YEAR", "📅", year_finds)
        if result:
            entities.append(result)

        # POWER
        power_finds = self.auto_find_power(text)
        result = self.label_entity_assisted(text, "POWER", "⚡", power_finds)
        if result:
            entities.append(result)

        # FUEL
        fuel_finds = self.auto_find_fuel(text)
        result = self.label_entity_assisted(text, "FUEL", "⛽", fuel_finds)
        if result:
            entities.append(result)

        print(f"\n✅ Labeled {len(entities)} entities")

        return text, {"entities": entities}

    def label_from_file(self, input_file: str, output_file: str, limit: int = None):
        """Label multiple texts with assistance"""

        # Read input
        if input_file.endswith('.json'):
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                texts = [item['text'] for item in data]
        else:
            print("❌ Error: Input must be a JSON file")
            return

        if limit:
            texts = texts[:limit]

        print(f"\n{'='*80}")
        print(f"🚀 Assisted Labeling Tool")
        print(f"{'='*80}")
        print(f"You'll label {len(texts)} examples")
        print(f"\nTips:")
        print(f"  - Press ENTER to accept suggestions")
        print(f"  - Type 's' or 'skip' to skip a field")
        print(f"  - Type manually if suggestion is wrong")
        print(f"  - Press Ctrl+C anytime to save and quit")
        print(f"{'='*80}\n")
        input("Press Enter to start...")

        labeled = []
        for i, text in enumerate(texts, 1):
            print(f"\n\n[{i}/{len(texts)}]")

            try:
                labeled_example = self.label_single_text(text)
                labeled.append(labeled_example)

                # Save progress after each one
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(labeled, f, ensure_ascii=False, indent=2)

                # Show stats
                total = sum(self.stats.values())
                if total > 0:
                    auto_pct = self.stats['auto_accepted'] / total * 100
                    print(f"\n📊 Session stats: {auto_pct:.0f}% auto-accepted, {len(labeled)} examples done")

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted! Progress saved.")
                break

        # Final summary
        print(f"\n\n{'='*80}")
        print(f"🎉 Labeling Complete!")
        print(f"{'='*80}")
        print(f"Examples labeled: {len(labeled)}")
        print(f"\n📊 Efficiency Stats:")
        print(f"  Auto-accepted:      {self.stats['auto_accepted']} ({self.stats['auto_accepted']/(sum(self.stats.values()) or 1)*100:.1f}%)")
        print(f"  Manually corrected: {self.stats['manually_corrected']}")
        print(f"  Manually entered:   {self.stats['manually_entered']}")
        print(f"  Skipped:            {self.stats['skipped']}")
        print(f"{'='*80}")
        print(f"\n💡 Saved to: {output_file}")

    def load_and_continue(self, output_file: str, input_file: str, limit: int = None):
        """Continue labeling from where you left off"""
        if Path(output_file).exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                self.labeled_data = json.load(f)
            print(f"✓ Loaded {len(self.labeled_data)} previously labeled examples")

        # Get remaining texts
        if input_file.endswith('.json'):
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_texts = [item['text'] for item in data]
        else:
            print("❌ Error: Input must be a JSON file")
            return

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
            print(f"\n\n[{i}/{len(self.labeled_data) + len(remaining_texts)}]")

            try:
                labeled_example = self.label_single_text(text)
                self.labeled_data.append(labeled_example)

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.labeled_data, f, ensure_ascii=False, indent=2)

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted! Progress saved.")
                break


def main():
    parser = argparse.ArgumentParser(description="Fast assisted labeling with regex pre-annotation")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", default="training_data_labeled.json", help="Output JSON file")
    parser.add_argument("--limit", type=int, help="Max examples to label")
    parser.add_argument("--continue", dest="continue_labeling", action="store_true",
                       help="Continue from existing labels")

    args = parser.parse_args()

    labeler = AssistedLabeler()

    if args.continue_labeling:
        labeler.load_and_continue(args.output, args.input, args.limit)
    else:
        labeler.label_from_file(args.input, args.output, args.limit)


if __name__ == "__main__":
    main()
