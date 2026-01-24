"""
Review Disagreements Interface
===============================

Manual review tool for cases where ML and Regex disagree.
This is where humans improve the training data by correcting mistakes.

Usage:
    python3 review_disagreements.py

Interactive prompts will guide you through each disagreement.
"""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import re


def parse_user_input(user_input: str, field: str):
    """
    Parse user input and extract the RAW value as it should appear in text.

    Handles inputs like:
    - "99000" → "99000"
    - "99 000 km" → "99 000 km" (keep RAW format)
    - "145 KW" → "145 KW" (keep RAW format)
    - "dieselový" → "dieselový" (keep RAW format)

    Args:
        user_input: The raw user input string
        field: The field type (mileage, year, power, fuel)

    Returns:
        The value in RAW format as it would appear in text
    """
    user_input = user_input.strip()

    # For fuel, just return as-is (it's text)
    if field == 'fuel':
        return user_input

    # For numeric fields (mileage, year, power):
    # Accept the input AS-IS (user types what they see in the text)
    # This preserves formatting like "99 000 km", "145 KW", etc.
    return user_input


class DisagreementReviewer:
    """Interactive tool for reviewing extraction disagreements"""

    def __init__(self,
                 review_queue_file: str = 'review_queue.json',
                 reviewed_data_file: str = 'manual_review_data.json'):
        self.review_queue_file = Path(review_queue_file)
        self.reviewed_data_file = Path(reviewed_data_file)

    def review_all(self):
        """Review all items in the queue"""
        if not self.review_queue_file.exists():
            print("✅ No disagreements to review!")
            return

        with open(self.review_queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)

        if not queue:
            print("✅ Review queue is empty!")
            return

        # Load already reviewed car IDs to skip duplicates
        reviewed_car_ids = set()
        if self.reviewed_data_file.exists():
            with open(self.reviewed_data_file, 'r', encoding='utf-8') as f:
                existing_reviews = json.load(f)
                reviewed_car_ids = {item.get('car_id') for item in existing_reviews if item.get('car_id')}

        # Filter out already reviewed cases
        original_queue_size = len(queue)
        queue = [case for case in queue if case.get('car_id') not in reviewed_car_ids]

        if len(queue) < original_queue_size:
            print(f"\n✓ Skipped {original_queue_size - len(queue)} already reviewed cases")

        if not queue:
            print("✅ All cases have been reviewed!")
            # Clear the queue file since everything is done
            if self.review_queue_file.exists():
                self.review_queue_file.unlink()
            return

        print(f"\n{'='*80}")
        print(f"🔍 Disagreement Review")
        print(f"{'='*80}")
        print(f"You have {len(queue)} cases to review")
        print(f"\nInstructions:")
        print(f"  - For each field, choose which extraction is correct")
        print(f"  - Type '1' for ML, '2' for Regex, '3' for Neither, or type the correct value")
        print(f"  - Type 'skip' to skip this example")
        print(f"  - Type 'quit' to save and exit")
        print(f"{'='*80}\n")

        input("Press Enter to start review...")

        reviewed_data = []
        skipped = []

        for i, case in enumerate(queue, 1):
            print(f"\n{'='*80}")
            print(f"Case {i}/{len(queue)} - Car ID: {case.get('car_id', 'Unknown')}")
            print(f"{'='*80}")
            print(f"Text: {case['text']}")
            print(f"\nDisagreements: {', '.join(case['comparison']['disagreements'])}")
            print()

            # Review each field
            corrected_result = {}
            skip_this_case = False

            for field in ['mileage', 'year', 'power', 'fuel']:
                ml_value = case['ml_result'].get(field)
                regex_value = case['regex_result'].get(field)

                if field in case['comparison']['disagreements']:
                    # They disagree - ask user
                    print(f"\n{'─'*40}")
                    print(f"⚠️  {field.upper()} - DISAGREEMENT:")
                    print(f"  1. ML found:    {ml_value}")
                    print(f"  2. Regex found: {regex_value}")

                    while True:
                        choice = input(f"  Which is correct? (1/2/3=Neither/custom value/skip): ").strip().lower()

                        if choice == 'skip':
                            print("  ⏭️  Skipping this example")
                            skipped.append(case)
                            skip_this_case = True
                            break
                        elif choice == 'quit':
                            print("\n💾 Saving progress and exiting...")
                            self._save_reviewed_data(reviewed_data, skipped, queue[i:])
                            return
                        elif choice == '1':
                            corrected_result[field] = ml_value
                            print(f"  ✓ Using ML: {ml_value}")
                            break
                        elif choice == '2':
                            corrected_result[field] = regex_value
                            print(f"  ✓ Using Regex: {regex_value}")
                            break
                        elif choice == '3':
                            corrected_result[field] = None
                            print(f"  ✓ Neither - field is empty")
                            break
                        else:
                            # Custom value - parse and accept as RAW
                            parsed_value = parse_user_input(choice, field)
                            corrected_result[field] = parsed_value
                            print(f"  ✓ Using custom value: {parsed_value}")
                            break

                    if skip_this_case:
                        break

                elif field in case['comparison']['ml_only']:
                    # Only ML found
                    print(f"\n{'─'*40}")
                    print(f"ℹ️  {field.upper()} - ML only:")
                    print(f"  ML found: {ml_value}")
                    print(f"  Regex found: Nothing")

                    choice = input(f"  Is ML correct? (y/n/custom value/skip/quit): ").strip().lower()

                    if choice == 'skip':
                        print("  ⏭️  Skipping this example")
                        skipped.append(case)
                        skip_this_case = True
                        break
                    elif choice == 'quit':
                        print("\n💾 Saving progress and exiting...")
                        self._save_reviewed_data(reviewed_data, skipped, queue[i:])
                        return
                    elif choice == 'y' or choice == '':
                        corrected_result[field] = ml_value
                        print(f"  ✓ Confirmed: {ml_value}")
                    elif choice == 'n':
                        corrected_result[field] = None
                        print(f"  ✓ Rejected - field is empty")
                    else:
                        # Custom value - parse and accept as RAW
                        parsed_value = parse_user_input(choice, field)
                        corrected_result[field] = parsed_value
                        print(f"  ✓ Using custom value: {parsed_value}")

                    if skip_this_case:
                        break

                elif field in case['comparison']['regex_only']:
                    # Only Regex found
                    print(f"\n{'─'*40}")
                    print(f"ℹ️  {field.upper()} - Regex only:")
                    print(f"  ML found: Nothing")
                    print(f"  Regex found: {regex_value}")

                    choice = input(f"  Is Regex correct? (y/n/custom value/skip/quit): ").strip().lower()

                    if choice == 'skip':
                        print("  ⏭️  Skipping this example")
                        skipped.append(case)
                        skip_this_case = True
                        break
                    elif choice == 'quit':
                        print("\n💾 Saving progress and exiting...")
                        self._save_reviewed_data(reviewed_data, skipped, queue[i:])
                        return
                    elif choice == 'y' or choice == '':
                        corrected_result[field] = regex_value
                        print(f"  ✓ Confirmed: {regex_value}")
                    elif choice == 'n':
                        corrected_result[field] = None
                        print(f"  ✓ Rejected - field is empty")
                    else:
                        # Custom value - parse and accept as RAW
                        parsed_value = parse_user_input(choice, field)
                        corrected_result[field] = parsed_value
                        print(f"  ✓ Using custom value: {parsed_value}")

                    if skip_this_case:
                        break

                else:
                    # Both agree or both empty
                    corrected_result[field] = ml_value  # Use ML value (they're the same)

            # Skip creating training example if user chose to skip
            if skip_this_case:
                print(f"\n⏭️  Case {i} skipped")
                continue

            # Convert to training format
            # Note: This is simplified - in production you'd want exact entity positions
            training_example = (case['text'], {'entities': self._create_entities(case['text'], corrected_result)})

            reviewed_data.append({
                'data': training_example,
                'car_id': case.get('car_id'),
                'timestamp': datetime.now().isoformat(),
                'source': 'manual_review'
            })

            print(f"\n✅ Case {i} reviewed and saved")

        # Save all reviewed data
        self._save_reviewed_data(reviewed_data, skipped, [])

        print(f"\n{'='*80}")
        print(f"✅ Review Complete!")
        print(f"{'='*80}")
        print(f"Reviewed: {len(reviewed_data)} cases")
        print(f"Skipped:  {len(skipped)} cases")
        print(f"\n💡 Next step: python3 retrain_model.py")
        print(f"{'='*80}\n")

    def _create_entities(self, text: str, result: Dict) -> List:
        """Create entity annotations from result - works with RAW values"""
        entities = []
        import re

        # Find mileage (RAW value like "160.373 km", "150 tis km")
        if result.get('mileage'):
            # Escape special regex chars in the RAW value
            mileage_escaped = re.escape(result['mileage'])
            # Try exact match first
            match = re.search(mileage_escaped, text, re.IGNORECASE)
            if match:
                entities.append((match.start(), match.end(), 'MILEAGE'))

        # Find year (RAW value like "2015")
        if result.get('year'):
            year_str = str(result['year'])
            pos = text.find(year_str)
            if pos != -1:
                entities.append((pos, pos + len(year_str), 'YEAR'))

        # Find power (RAW value like "88 kw", "145 KW")
        if result.get('power'):
            # Escape special regex chars in the RAW value
            power_escaped = re.escape(result['power'])
            match = re.search(power_escaped, text, re.IGNORECASE)
            if match:
                entities.append((match.start(), match.end(), 'POWER'))

        # Find fuel (RAW value like "dieselový", "BENZIN")
        if result.get('fuel'):
            fuel_escaped = re.escape(result['fuel'])
            match = re.search(fuel_escaped, text, re.IGNORECASE)
            if match:
                entities.append((match.start(), match.end(), 'FUEL'))

        return entities

    def _save_reviewed_data(self, reviewed: List, skipped: List, remaining: List):
        """Save reviewed data and update queue"""
        # Save reviewed data
        if reviewed:
            existing = []
            if self.reviewed_data_file.exists():
                with open(self.reviewed_data_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)

            existing.extend(reviewed)

            with open(self.reviewed_data_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            print(f"\n💾 Saved {len(reviewed)} reviewed cases to {self.reviewed_data_file}")

        # Update review queue (keep skipped and remaining)
        new_queue = skipped + remaining

        if new_queue:
            with open(self.review_queue_file, 'w', encoding='utf-8') as f:
                json.dump(new_queue, f, ensure_ascii=False, indent=2)
            print(f"💾 Updated review queue: {len(new_queue)} items remaining")
        else:
            # Clear the queue
            if self.review_queue_file.exists():
                self.review_queue_file.unlink()
            print(f"🗑️  Review queue cleared")


def main():
    reviewer = DisagreementReviewer()
    reviewer.review_all()


if __name__ == "__main__":
    main()
