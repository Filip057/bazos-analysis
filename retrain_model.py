#!/usr/bin/env python3
"""
Quick Retrain Script
--------------------
Convenient entry point for retraining the model with new GPT-labeled data.

Usage:
    python3 retrain_model.py

This script:
  1. Checks if auto_labeled_193.json exists (GPT output)
  2. Combines with existing training_data_fixed.json
  3. Trains model (30 iterations)
  4. Tests model (shows F1 score)
  5. Compares with previous model

If you need more control, use:
    python3 combine_and_train.py --help
"""

import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("🚀 QUICK RETRAIN WORKFLOW")
    print("=" * 70)
    print()

    # Check if GPT labeled data exists
    if not Path('auto_labeled_193.json').exists():
        print("❌ ERROR: auto_labeled_193.json not found!")
        print()
        print("💡 You need to complete GPT labeling first!")
        print()
        print("Steps:")
        print("  1. cat gpt_entity_extraction_prompt_v2.md")
        print("  2. Copy prompt to GPT-4/Claude")
        print("  3. Add content of unlabeled_for_gpt.json")
        print("  4. Save GPT output as auto_labeled_193.json")
        print()
        print("📖 See LABELING_INSTRUCTIONS.md for detailed help:")
        print("   cat LABELING_INSTRUCTIONS.md")
        print()
        sys.exit(1)

    print("✅ Found auto_labeled_193.json")
    print()
    print("🔄 Starting combine + train workflow...")
    print()

    # Import and run combine_and_train
    try:
        import combine_and_train
        combine_and_train.main()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("💡 Try running manually:")
        print("   python3 combine_and_train.py")
        sys.exit(1)

if __name__ == '__main__':
    main()
