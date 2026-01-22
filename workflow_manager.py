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

    def scrape_data(self):
        """Option 1: Scrape data"""
        self.print_header()
        print("📊 SCRAPE DATA")
        print("-" * 70)
        print()
        print("This will scrape car listings from Bazos.cz and extract data using")
        print("ML + Regex (RAW values - no normalization).")
        print()
        print("Options:")
        print("  1. Scrape WITHOUT database (--skip-db) [Recommended for testing]")
        print("  2. Scrape WITH database")
        print("  3. Back to main menu")
        print()

        choice = input("Choose option (1-3): ").strip()

        if choice == '1':
            self.run_command(
                "python3 -m scraper.data_scrap --skip-db",
                "Scraping data (without database)"
            )
        elif choice == '2':
            self.run_command(
                "python3 -m scraper.data_scrap",
                "Scraping data (with database)"
            )
        else:
            return

        input("\nPress Enter to continue...")

    def clean_duplicates(self):
        """Option 2: Clean duplicates"""
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
        """Option 3: Review disagreements"""
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

    def retrain_model(self):
        """Option 4: Retrain model"""
        self.print_header()
        print("🎓 RETRAIN MODEL")
        print("-" * 70)
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
            print("❌ No training data found! Cannot retrain.")
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

    def view_stats(self):
        """Option 5: View statistics"""
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
        """Option 6: Normalize data"""
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
        """Option 7: Reset workflow"""
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
        print("  1. 📊 Scrape Data               - Get car listings with RAW extraction")
        print("  2. 🧹 Clean Duplicates          - Remove duplicate review entries")
        print("  3. 🔍 Review Disagreements      - Label RAW data for training")
        print("  4. 🎓 Retrain Model             - Retrain with accumulated data")
        print("  5. 📈 View Statistics           - Check extraction accuracy")
        print("  6. 🔧 Normalize Data            - Preview normalization (DB format)")
        print("  7. ⚠️  Reset Workflow            - Delete all generated files")
        print("  8. 📖 View Documentation        - Open WORKFLOW.md")
        print("  9. ❌ Exit")
        print("-" * 70)
        print()

        choice = input("Choose option (1-9): ").strip()

        return choice

    def view_documentation(self):
        """Option 8: View documentation"""
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
                    self.scrape_data()
                elif choice == '2':
                    self.clean_duplicates()
                elif choice == '3':
                    self.review_disagreements()
                elif choice == '4':
                    self.retrain_model()
                elif choice == '5':
                    self.view_stats()
                elif choice == '6':
                    self.normalize_data()
                elif choice == '7':
                    self.reset_workflow()
                elif choice == '8':
                    self.view_documentation()
                elif choice == '9':
                    self.print_header()
                    print("👋 Goodbye!")
                    print()
                    sys.exit(0)
                else:
                    print("\n❌ Invalid option. Please choose 1-9.")
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
