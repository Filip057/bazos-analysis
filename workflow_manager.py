#!/usr/bin/env python3
"""
ML Training Workflow Manager
=============================

Interactive CLI tool to manage the complete ML training workflow.
Combines all steps into one easy-to-use menu interface.

Usage:
    python3 workflow_manager.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional


class WorkflowManager:
    """Interactive workflow management"""

    def __init__(self):
        self.project_root = Path.cwd()

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')

    def print_header(self):
        """Print menu header"""
        self.clear_screen()
        print("=" * 70)
        print("🚀 ML Training Workflow Manager")
        print("=" * 70)
        print()

    def check_file_status(self):
        """Check status of key files"""
        files = {
            'review_queue.json': 'Disagreements to review',
            'manual_review_data.json': 'Manual corrections',
            'auto_training_data.json': 'Auto-collected training',
            'extraction_stats.json': 'Extraction statistics',
            'training_data_labeled.json': 'Original training data'
        }

        print("📁 File Status:")
        print("-" * 70)

        for filename, description in files.items():
            path = self.project_root / filename
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        count = len(data) if isinstance(data, list) else "N/A"
                    print(f"  ✓ {filename:<30} {description:<30} ({count} items)")
                except:
                    print(f"  ✓ {filename:<30} {description:<30} (exists)")
            else:
                print(f"  ✗ {filename:<30} {description:<30} (not found)")

        print()

    def run_command(self, command: str, description: str, capture_output: bool = False):
        """Run a shell command with status output"""
        print(f"\n{'='*70}")
        print(f"▶️  {description}")
        print(f"{'='*70}")
        print(f"Command: {command}")
        print()

        input("Press Enter to continue (Ctrl+C to cancel)...")
        print()

        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
                return result.returncode == 0
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.project_root
                )
                return result.returncode == 0
        except KeyboardInterrupt:
            print("\n⚠️  Command cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

    def scrape_for_training(self):
        """Option 1: Scrape real data from Bazos for training"""
        self.print_header()
        print("🌐 SCRAPE FOR TRAINING")
        print("-" * 70)
        print()
        print("This scrapes REAL car descriptions from Bazos.cz for labeling.")
        print("Much better than synthetic examples!")
        print()
        print("You can scrape:")
        print("  • Single brand (e.g., 'skoda' or 'toyota')")
        print("  • Multiple brands with counts (e.g., 'toyota:17 skoda:17')")
        print()

        choice = input("Choose: (1) Single brand  (2) Mixed brands  (3) Cancel: ").strip()

        if choice == '1':
            brand = input("Enter brand name (e.g., skoda, toyota, volkswagen): ").strip().lower()
            if not brand:
                print("❌ Brand name required!")
                input("\nPress Enter to continue...")
                return

            limit = input("How many cars to scrape? (default: 50): ").strip()
            if not limit:
                limit = "50"

            output = f"training_{brand}.json"

            self.run_command(
                f'python3 -m labeling.scrape_for_training --brand {brand} --limit {limit} --output "{output}"',
                f"Scraping {limit} {brand} cars for training"
            )

        elif choice == '2':
            print()
            print("Enter brands with counts, e.g.: toyota:17 skoda:17 volkswagen:16")
            brands = input("Brands: ").strip()
            if not brands:
                print("❌ Brands required!")
                input("\nPress Enter to continue...")
                return

            output = input("Output filename (default: training_mixed.json): ").strip()
            if not output:
                output = "training_mixed.json"

            self.run_command(
                f'python3 -m labeling.scrape_mixed_brands --brands {brands} --output "{output}"',
                "Scraping mixed brands for training"
            )
        else:
            return

        input("\nPress Enter to continue...")

    def filter_training_data(self):
        """Option 2: Filter training data - keep only rich examples"""
        self.print_header()
        print("🔍 FILTER TRAINING DATA")
        print("-" * 70)
        print()
        print("This filters out examples with no useful data.")
        print("Keeps only examples where regex found at least 1/4 fields.")
        print()
        print("This saves time - you won't label empty examples!")
        print()

        # Show available raw training files
        print("Available training files:")
        training_files = list(self.project_root.glob("training_*.json"))
        if not training_files:
            print("❌ No training_*.json files found!")
            print()
            print("Run 'Scrape For Training' first to get raw data.")
            input("\nPress Enter to continue...")
            return

        for i, file in enumerate(training_files, 1):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    print(f"  {i}. {file.name} ({len(data)} examples)")
            except:
                print(f"  {i}. {file.name}")

        print()
        input_file = input("Enter input filename (e.g., training_skoda.json): ").strip()
        if not input_file:
            print("❌ Filename required!")
            input("\nPress Enter to continue...")
            return

        output_file = input("Enter output filename (default: filtered_training_skoda.json): ").strip()
        if not output_file:
            output_file = f"filtered_{input_file}"

        self.run_command(
            f'python3 -m labeling.filter_training_data --input "{input_file}" --output "{output_file}"',
            "Filtering training data"
        )

        input("\nPress Enter to continue...")

    def label_data_assisted(self):
        """Option 4: Label data with regex assistance (FASTER)"""
        self.print_header()
        print("🚀 LABEL DATA (ASSISTED - MUCH FASTER!)")
        print("-" * 70)
        print()
        print("This is 5-10x FASTER than manual labeling!")
        print()
        print("How it works:")
        print("  • Regex automatically finds entities and highlights them")
        print("  • You just press Enter to accept or type correction")
        print("  • Perfect for quick labeling of 50-100 examples")
        print()

        # Check if filtered data exists
        input_file = self.project_root / 'filtered_training_skoda.json'
        output_file = self.project_root / 'training_data_labeled.json'

        # Show available filtered files
        print("Available filtered files:")
        filtered_files = list(self.project_root.glob("filtered_*.json"))
        if not filtered_files:
            print("❌ No filtered_*.json files found!")
            print()
            print("Run 'Filter Training Data' first to prepare data.")
            input("\nPress Enter to continue...")
            return

        for i, file in enumerate(filtered_files, 1):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    print(f"  {i}. {file.name} ({len(data)} examples)")
            except:
                print(f"  {i}. {file.name}")

        print()
        input_choice = input("Enter input filename (default: filtered_training_skoda.json): ").strip()
        if input_choice:
            input_file = self.project_root / input_choice

        if not input_file.exists():
            print(f"❌ {input_file.name} not found!")
            input("\nPress Enter to continue...")
            return

        print()
        print("How many examples to label?")
        print("(Recommendation: 50-100 for good initial model)")
        limit = input("Enter number (or press Enter for 50): ").strip()
        if not limit:
            limit = "50"

        self.run_command(
            f'python3 -m labeling.label_data_assisted --input "{input_file}" --output "{output_file}" --limit {limit}',
            f"Assisted labeling of {limit} examples"
        )

        input("\nPress Enter to continue...")

    def label_new_data(self):
        """Option 3: Label new data manually"""
        self.print_header()
        print("📝 LABEL NEW DATA")
        print("-" * 70)
        print()
        print("This tool helps you create training data for the ML model.")
        print("You'll manually label entities (MILEAGE, YEAR, POWER, FUEL) in car descriptions.")
        print()

        # Check if filtered_training_skoda.json exists
        input_file = self.project_root / 'filtered_training_skoda.json'
        output_file = self.project_root / 'training_data_labeled.json'

        if not input_file.exists():
            print("❌ filtered_training_skoda.json not found!")
            print()
            print("You need to prepare a JSON file with car descriptions first.")
            print("See labeling/filter_training_data.py for help.")
            input("\nPress Enter to continue...")
            return

        print(f"Input file:  {input_file.name}")
        print(f"Output file: {output_file.name}")
        print()
        print("How many examples do you want to label?")
        print("(Recommendation: Start with 30-50 for initial model)")
        print()

        limit = input("Enter number of examples (or press Enter for 30): ").strip()
        if not limit:
            limit = "30"

        self.run_command(
            f'python3 -m labeling.label_data --input "{input_file}" --output "{output_file}" --limit {limit}',
            f"Labeling {limit} examples"
        )

    def validate_labels(self):
        """Option 5: Validate labeled data"""
        self.print_header()
        print("✅ VALIDATE LABELS")
        print("-" * 70)
        print()
        print("This tool checks for labeling errors:")
        print("  • Overlapping entities (same text labeled as multiple types)")
        print("  • Misaligned entities (text not found in original)")
        print("  • Invalid ranges")
        print()

        training_file = self.project_root / 'training_data_labeled.json'

        if not training_file.exists():
            print("❌ training_data_labeled.json not found!")
            print()
            print("You need to label data first using Option 1 (Label New Data)")
            input("\nPress Enter to continue...")
            return

        print(f"Validating: {training_file.name}")
        print()

        self.run_command(
            f'python3 labeling/validate_labels.py "{training_file}"',
            "Validating labeled data"
        )

    def scrape_data(self):
        """Option 6: Scrape data"""
        self.print_header()
        print("📊 SCRAPE DATA")
        print("-" * 70)
        print()
        print("This will scrape car listings from Bazos.cz and extract data using")
        print("ML + Regex (RAW values - no normalization).")
        print()
        print("Available brands:")
        print("  alfa, audi, bmw, citroen, dacia, fiat, ford, honda, hyundai,")
        print("  chevrolet, kia, mazda, mercedes, mitsubishi, nissan, opel,")
        print("  peugeot, renault, seat, suzuki, skoda, toyota, volkswagen, volvo")
        print()
        print("Options:")
        print("  1. Scrape specific brand(s)")
        print("  2. Scrape ALL brands")
        print("  3. Back to main menu")
        print()

        choice = input("Choose option (1-3): ").strip()

        if choice == '1':
            brands = input("\nEnter brand(s) (space-separated, e.g., 'skoda toyota'): ").strip()
            if not brands:
                print("❌ No brands specified!")
                input("\nPress Enter to continue...")
                return

            print()
            print("Database options:")
            print("  1. Skip database (testing mode)")
            print("  2. Save to database")
            db_choice = input("Choose (1-2): ").strip()

            skip_db = "--skip-db" if db_choice == '1' else ""

            self.run_command(
                f"python3 -m scraper.data_scrap --brands {brands} {skip_db}",
                f"Scraping {brands}"
            )

        elif choice == '2':
            print()
            print("⚠️  WARNING: Scraping ALL brands may take a long time!")
            print()
            print("Database options:")
            print("  1. Skip database (testing mode)")
            print("  2. Save to database")
            db_choice = input("Choose (1-2): ").strip()

            confirm = input("\nProceed with scraping all brands? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("❌ Cancelled")
                input("\nPress Enter to continue...")
                return

            skip_db = "--skip-db" if db_choice == '1' else ""

            self.run_command(
                f"python3 -m scraper.data_scrap {skip_db}",
                "Scraping ALL brands"
            )
        else:
            return

        input("\nPress Enter to continue...")

    def clean_duplicates(self):
        """Option 7: Clean duplicates"""
        self.print_header()
        print("🧹 CLEAN DUPLICATES")
        print("-" * 70)
        print()
        print("Remove duplicate entries from review files based on unique car URLs.")
        print()
        print("Options:")
        print("  1. Clean review_queue.json only")
        print("  2. Clean manual_review_data.json only")
        print("  3. Clean both files")
        print("  4. Back to main menu")
        print()

        choice = input("Choose option (1-4): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m ml.deduplicate_review_queue",
                "Cleaning review_queue.json"
            )
        elif choice == '2':
            self.run_command(
                "python3 -m ml.deduplicate_manual_reviews",
                "Cleaning manual_review_data.json"
            )
        elif choice == '3':
            self.run_command(
                "python3 -m ml.clean_all_duplicates",
                "Cleaning all duplicate files"
            )
        else:
            return

        input("\nPress Enter to continue...")

    def review_disagreements(self):
        """Option 8: Review disagreements"""
        self.print_header()
        print("🔍 REVIEW DISAGREEMENTS")
        print("-" * 70)
        print()

        # Check if review queue exists
        queue_path = self.project_root / 'review_queue.json'
        if not queue_path.exists():
            print("❌ No review_queue.json found!")
            print()
            print("Please run 'Scrape Data' first to generate disagreements.")
            input("\nPress Enter to continue...")
            return

        # Show queue size
        try:
            with open(queue_path, 'r') as f:
                queue = json.load(f)
                print(f"📋 Review Queue: {len(queue)} cases to review")
        except:
            print("⚠️  Could not read review_queue.json")

        print()
        print("This will start the interactive review interface where you label")
        print("RAW data as it appears in the text.")
        print()
        print("Commands during review:")
        print("  - Type '1' for ML, '2' for Regex, '3' for Neither")
        print("  - Type 'skip' to skip a case")
        print("  - Type 'quit' to save progress and exit")
        print()

        self.run_command(
            "python3 -m ml.review_disagreements",
            "Starting disagreement review"
        )

        input("\nPress Enter to continue...")

    def train_initial_model(self):
        """Option 9: Train initial model from scratch"""
        self.print_header()
        print("🎓 TRAIN INITIAL MODEL (First Time)")
        print("-" * 70)
        print()
        print("This trains a NEW model from your original labeled data.")
        print("Use this on a new machine or when starting fresh.")
        print()

        # Check if training data exists
        training_file = self.project_root / 'training_data_labeled.json'
        if not training_file.exists():
            print("❌ training_data_labeled.json not found!")
            print()
            print("You need labeled training data to train a model.")
            input("\nPress Enter to continue...")
            return

        # Check data quality
        try:
            with open(training_file, 'r') as f:
                data = json.load(f)
                count = len(data)
                print(f"📊 Training data: {count} labeled examples")
        except:
            print("⚠️  Could not read training_data_labeled.json")
            count = 0

        if count < 50:
            print()
            print("⚠️  WARNING: Less than 50 examples!")
            print("   Recommended: At least 100-200 examples for good accuracy")

        print()
        print("Options:")
        print("  1. Train with default settings (30 iterations)")
        print("  2. Train with custom iterations")
        print("  3. Analyze training data quality first")
        print("  4. Back to main menu")
        print()

        choice = input("Choose option (1-4): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m ml.train_ml_model --data training_data_labeled.json --iterations 30",
                "Training initial model (30 iterations)"
            )
        elif choice == '2':
            iterations = input("Number of iterations (recommended 30-100): ").strip()
            iterations = iterations if iterations else "30"
            self.run_command(
                f"python3 -m ml.train_ml_model --data training_data_labeled.json --iterations {iterations}",
                f"Training initial model ({iterations} iterations)"
            )
        elif choice == '3':
            self.check_training_data_quality()
            return self.train_initial_model()  # Return to this menu
        else:
            return

        input("\nPress Enter to continue...")

    def retrain_model(self):
        """Option 10: Retrain model with accumulated data"""
        self.print_header()
        print("🔄 RETRAIN MODEL (With New Data)")
        print("-" * 70)
        print()
        print("This retrains your existing model with accumulated production data.")
        print()

        # Check data sources
        print("Data sources:")
        sources = {
            'training_data_labeled.json': 'Original labeled data',
            'auto_training_data.json': 'Auto-collected (agreements)',
            'manual_review_data.json': 'Manual corrections'
        }

        total_examples = 0
        for filename, description in sources.items():
            path = self.project_root / filename
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        count = len(data)
                        total_examples += count
                        print(f"  ✓ {filename:<30} {count:>4} examples")
                except:
                    print(f"  ✓ {filename:<30} (exists)")
            else:
                print(f"  ✗ {filename:<30} (not found)")

        print()
        print(f"Total training examples: {total_examples}")
        print()

        if total_examples == 0:
            print("❌ No training data found!")
            print()
            print("💡 Use 'Train Initial Model' first to create a model from scratch.")
            input("\nPress Enter to continue...")
            return

        print("Options:")
        print("  1. Retrain with default settings (100 iterations)")
        print("  2. Retrain with custom iterations")
        print("  3. Back to main menu")
        print()

        choice = input("Choose option (1-3): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m ml.retrain_model",
                "Retraining model (100 iterations)"
            )
        elif choice == '2':
            iterations = input("Number of iterations (default 100): ").strip()
            iterations = iterations if iterations else "100"
            self.run_command(
                f"python3 -m ml.retrain_model --iterations {iterations}",
                f"Retraining model ({iterations} iterations)"
            )
        else:
            return

        input("\nPress Enter to continue...")

    def evaluate_model_quality(self):
        """Option 11: Evaluate model quality"""
        self.print_header()
        print("📊 EVALUATE MODEL QUALITY")
        print("-" * 70)
        print()

        # Check if model exists
        model_path = self.project_root / 'ml_models' / 'car_ner'
        if not model_path.exists():
            print("❌ No trained model found!")
            print()
            print("💡 Train a model first using 'Train Initial Model'")
            input("\nPress Enter to continue...")
            return

        # Check if test data exists
        training_file = self.project_root / 'training_data_labeled.json'
        if not training_file.exists():
            print("❌ training_data_labeled.json not found!")
            print()
            print("Cannot evaluate without test data.")
            input("\nPress Enter to continue...")
            return

        print("This will evaluate your model against test data to measure accuracy.")
        print()
        print("Metrics shown:")
        print("  - Precision: How many predictions are correct")
        print("  - Recall: How many true entities are found")
        print("  - F1 Score: Balance between precision and recall (target: 80%+)")
        print()
        print("Options:")
        print("  1. Evaluate current model")
        print("  2. Evaluate with custom test split (default 20%)")
        print("  3. Back to main menu")
        print()

        choice = input("Choose option (1-3): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m ml.train_ml_model --data training_data_labeled.json --evaluate-only",
                "Evaluating model quality"
            )
        elif choice == '2':
            test_split = input("Test split percentage (default 20): ").strip()
            test_split = test_split if test_split else "20"
            test_split_decimal = float(test_split) / 100
            self.run_command(
                f"python3 -m ml.train_ml_model --data training_data_labeled.json --evaluate-only --test-split {test_split_decimal}",
                f"Evaluating model (test split: {test_split}%)"
            )
        else:
            return

        input("\nPress Enter to continue...")

    def check_training_data_quality(self):
        """Option 12: Check training data quality"""
        self.print_header()
        print("🔍 CHECK TRAINING DATA QUALITY")
        print("-" * 70)
        print()

        # Check all training data sources
        sources = {
            'training_data_labeled.json': 'Original labeled data',
            'auto_training_data.json': 'Auto-collected (agreements)',
            'manual_review_data.json': 'Manual corrections'
        }

        print("This analyzes your training data for:")
        print("  - Entity distribution (MILEAGE, YEAR, POWER, FUEL)")
        print("  - Labeling errors (invalid positions)")
        print("  - Data balance")
        print()

        print("Available files:")
        files_to_check = []
        for filename, description in sources.items():
            path = self.project_root / filename
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        count = len(data)
                        print(f"  ✓ {filename:<30} {count:>4} examples")
                        files_to_check.append(filename)
                except:
                    print(f"  ✓ {filename:<30} (exists)")
            else:
                print(f"  ✗ {filename:<30} (not found)")

        if not files_to_check:
            print()
            print("❌ No training data files found!")
            input("\nPress Enter to continue...")
            return

        print()
        print("Options:")
        print("  1. Check original labeled data")
        print("  2. Check all training data sources combined")
        print("  3. Back to main menu")
        print()

        choice = input("Choose option (1-3): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m ml.train_ml_model --data training_data_labeled.json --analyze-only",
                "Analyzing original labeled data"
            )
        elif choice == '2':
            # Combine all sources for analysis
            print()
            print("Analyzing all training data sources...")
            combined_data = []

            for filename in files_to_check:
                try:
                    with open(self.project_root / filename, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, (list, tuple)):
                                    combined_data.append(item)
                                elif isinstance(item, dict) and 'data' in item:
                                    combined_data.append(item['data'])
                except Exception as e:
                    print(f"  ⚠️  Could not read {filename}: {e}")

            # Save temporarily
            temp_file = self.project_root / 'temp_combined_training.json'
            with open(temp_file, 'w') as f:
                json.dump(combined_data, f, ensure_ascii=False, indent=2)

            print(f"  Combined {len(combined_data)} examples from all sources")
            print()

            self.run_command(
                "python3 -m ml.train_ml_model --data temp_combined_training.json --analyze-only",
                "Analyzing combined training data"
            )

            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()
        else:
            return

        input("\nPress Enter to continue...")

    def view_stats(self):
        """Option 13: View statistics"""
        self.print_header()
        print("📊 EXTRACTION STATISTICS")
        print("-" * 70)
        print()

        stats_path = self.project_root / 'extraction_stats.json'

        if not stats_path.exists():
            print("❌ No extraction_stats.json found!")
            print()
            print("Run 'Scrape Data' first to generate statistics.")
        else:
            try:
                with open(stats_path, 'r') as f:
                    stats = json.load(f)

                print("Overall Statistics:")
                print(f"  Total extractions:     {stats.get('total_extractions', 0)}")
                print(f"  Full agreements:       {stats.get('full_agreements', 0)} ({stats.get('full_agreements', 0) / max(stats.get('total_extractions', 1), 1) * 100:.1f}%)")
                print(f"  Partial agreements:    {stats.get('partial_agreements', 0)}")
                print(f"  Disagreements:         {stats.get('disagreements', 0)} ({stats.get('disagreements', 0) / max(stats.get('total_extractions', 1), 1) * 100:.1f}%)")
                print(f"  ML only:              {stats.get('ml_only', 0)}")
                print(f"  Regex only:           {stats.get('regex_only', 0)}")
                print(f"  Both empty:           {stats.get('both_empty', 0)}")
                print()

                print("Field Statistics:")
                field_stats = stats.get('field_stats', {})
                for field in ['mileage', 'year', 'power', 'fuel']:
                    field_data = field_stats.get(field, {})
                    agree = field_data.get('agree', 0)
                    disagree = field_data.get('disagree', 0)
                    total = agree + disagree
                    accuracy = (agree / total * 100) if total > 0 else 0
                    print(f"  {field.capitalize():<12} {accuracy:>5.1f}% accuracy ({agree}/{total} agree)")

            except Exception as e:
                print(f"❌ Error reading stats: {e}")

        input("\nPress Enter to continue...")

    def normalize_data(self):
        """Option 14: Normalize data"""
        self.print_header()
        print("🔧 NORMALIZE DATA")
        print("-" * 70)
        print()
        print("Preview how normalization works (RAW → Database format).")
        print()
        print("Options:")
        print("  1. Normalize review_queue.json (preview)")
        print("  2. Normalize custom file")
        print("  3. Test single extraction")
        print("  4. Back to main menu")
        print()

        choice = input("Choose option (1-4): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m ml.normalize_for_db --review-queue",
                "Normalizing review_queue.json (preview)"
            )
        elif choice == '2':
            filename = input("Enter file path: ").strip()
            if filename:
                self.run_command(
                    f'python3 -m ml.normalize_for_db --file "{filename}"',
                    f"Normalizing {filename}"
                )
        elif choice == '3':
            print()
            print("Enter JSON extraction (e.g., {\"fuel\":\"dieselový\",\"power\":\"145 KW\"})")
            extraction = input("> ").strip()
            if extraction:
                self.run_command(
                    f"python3 -m ml.normalize_for_db --text '{extraction}'",
                    "Normalizing single extraction"
                )
        else:
            return

        input("\nPress Enter to continue...")

    def reset_workflow(self):
        """Option 15: Reset workflow"""
        self.print_header()
        print("⚠️  RESET WORKFLOW")
        print("-" * 70)
        print()
        print("This will DELETE the following files:")
        print("  - review_queue.json")
        print("  - manual_review_data.json")
        print("  - auto_training_data.json")
        print("  - extraction_stats.json")
        print()
        print("Use this when you want to start fresh with new RAW data.")
        print()
        print("⚠️  WARNING: This action cannot be undone!")
        print()

        confirm = input("Type 'yes' to confirm deletion: ").strip().lower()

        if confirm != 'yes':
            print("❌ Reset cancelled")
            input("\nPress Enter to continue...")
            return

        files_to_delete = [
            'review_queue.json',
            'manual_review_data.json',
            'auto_training_data.json',
            'extraction_stats.json'
        ]

        deleted = 0
        for filename in files_to_delete:
            path = self.project_root / filename
            if path.exists():
                try:
                    path.unlink()
                    print(f"  ✓ Deleted {filename}")
                    deleted += 1
                except Exception as e:
                    print(f"  ❌ Failed to delete {filename}: {e}")
            else:
                print(f"  ⚠️  {filename} not found (already deleted?)")

        print()
        print(f"✅ Reset complete! Deleted {deleted} files.")
        print()
        print("Next step: Run 'Scrape Data' to generate fresh RAW extractions.")

        input("\nPress Enter to continue...")

    def show_menu(self):
        """Show main menu"""
        self.print_header()
        self.check_file_status()

        print("WORKFLOW OPTIONS:")
        print("-" * 70)
        print("\n📝 DATA LABELING (Create Training Data):")
        print("  1. Scrape For Training       - Scrape real Bazos data for labeling")
        print("  2. Filter Training Data      - Keep only rich examples")
        print("  3. Label Data (Manual)       - Manual labeling tool")
        print("  4. Label Data (Assisted)     - Assisted labeling with regex (FASTER)")
        print("  5. Validate Labels           - Check for labeling errors")
        print()
        print("📊 DATA COLLECTION:")
        print("  6. Scrape Data               - Get car listings with RAW extraction")
        print("  7. Clean Duplicates          - Remove duplicate review entries")
        print("  8. Review Disagreements      - Label RAW data for training")
        print()
        print("🎓 MODEL TRAINING & QUALITY:")
        print("  9. Train Initial Model       - First time training (from scratch)")
        print(" 10. Retrain Model             - Retrain with accumulated data")
        print(" 11. Evaluate Model Quality    - Test model accuracy (F1 score)")
        print(" 12. Check Training Data       - Analyze data quality & distribution")
        print()
        print("🔧 TOOLS & UTILITIES:")
        print(" 13. View Statistics           - Check extraction accuracy")
        print(" 14. Normalize Data            - Preview normalization (DB format)")
        print(" 15. Reset Workflow            - Delete all generated files")
        print(" 16. View Documentation        - Open WORKFLOW.md")
        print(" 17. Exit")
        print("-" * 70)
        print()

        choice = input("Choose option (1-17): ").strip()

        return choice

    def view_documentation(self):
        """Option 16: View documentation"""
        self.print_header()
        print("📖 DOCUMENTATION")
        print("-" * 70)
        print()

        doc_path = self.project_root / 'WORKFLOW.md'

        if not doc_path.exists():
            print("❌ WORKFLOW.md not found!")
        else:
            # Try to open with system viewer
            try:
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', str(doc_path)])
                elif sys.platform == 'linux':
                    subprocess.run(['xdg-open', str(doc_path)])
                else:  # Windows
                    subprocess.run(['start', str(doc_path)], shell=True)

                print("✓ Opening WORKFLOW.md in default viewer...")
            except:
                # Fallback: show in terminal
                print("Displaying WORKFLOW.md:\n")
                with open(doc_path, 'r') as f:
                    print(f.read())

        input("\nPress Enter to continue...")

    def run(self):
        """Main loop"""
        while True:
            try:
                choice = self.show_menu()

                if choice == '1':
                    self.scrape_for_training()
                elif choice == '2':
                    self.filter_training_data()
                elif choice == '3':
                    self.label_new_data()
                elif choice == '4':
                    self.label_data_assisted()
                elif choice == '5':
                    self.validate_labels()
                elif choice == '6':
                    self.scrape_data()
                elif choice == '7':
                    self.clean_duplicates()
                elif choice == '8':
                    self.review_disagreements()
                elif choice == '9':
                    self.train_initial_model()
                elif choice == '10':
                    self.retrain_model()
                elif choice == '11':
                    self.evaluate_model_quality()
                elif choice == '12':
                    self.check_training_data_quality()
                elif choice == '13':
                    self.view_stats()
                elif choice == '14':
                    self.normalize_data()
                elif choice == '15':
                    self.reset_workflow()
                elif choice == '16':
                    self.view_documentation()
                elif choice == '17':
                    self.print_header()
                    print("👋 Goodbye!")
                    print()
                    sys.exit(0)
                else:
                    print("\n❌ Invalid option. Please choose 1-17.")
                    input("Press Enter to continue...")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                sys.exit(0)
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("Press Enter to continue...")


def main():
    manager = WorkflowManager()
    manager.run()


if __name__ == "__main__":
    main()
