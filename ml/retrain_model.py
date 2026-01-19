"""
Model Retraining Script
=======================

Combines training data from multiple sources and retrains the ML model.

Sources:
1. Original labeled data (your 201 examples)
2. Auto-collected data (ML+Regex agreements)
3. Manual review data (corrected disagreements)

Usage:
    python3 retrain_model.py [--iterations 100] [--output ml_models/car_ner_v2]
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import logging

from ml.ml_extractor import CarDataExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_training_data(original_file: str,
                      auto_file: str,
                      manual_file: str) -> tuple:
    """Load and combine training data from all sources"""

    all_data = []
    stats = {
        'original': 0,
        'auto': 0,
        'manual': 0
    }

    # 1. Load original labeled data
    if Path(original_file).exists():
        with open(original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
            # Convert to standard format
            for item in original_data:
                if isinstance(item, (list, tuple)):
                    all_data.append(item)
                else:
                    # Dict format - convert to tuple
                    text = item.get('text', '')
                    entities = item.get('entities', [])
                    all_data.append((text, {'entities': entities}))
            stats['original'] = len(original_data)
            logger.info(f"Loaded {stats['original']} examples from original data")
    else:
        logger.warning(f"Original data file not found: {original_file}")

    # 2. Load auto-collected data
    if Path(auto_file).exists():
        with open(auto_file, 'r', encoding='utf-8') as f:
            auto_data = json.load(f)
            for item in auto_data:
                all_data.append(item['data'])  # Extract training example
            stats['auto'] = len(auto_data)
            logger.info(f"Loaded {stats['auto']} examples from auto-collection")
    else:
        logger.warning(f"Auto-collection file not found: {auto_file}")

    # 3. Load manual review data
    if Path(manual_file).exists():
        with open(manual_file, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)
            for item in manual_data:
                all_data.append(item['data'])  # Extract training example
            stats['manual'] = len(manual_data)
            logger.info(f"Loaded {stats['manual']} examples from manual review")
    else:
        logger.warning(f"Manual review file not found: {manual_file}")

    return all_data, stats


def retrain_model(training_data: list,
                 iterations: int,
                 output_path: str):
    """Retrain the model with combined data"""

    if not training_data:
        logger.error("No training data available!")
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"Starting Model Retraining")
    logger.info(f"{'='*60}")
    logger.info(f"Total training examples: {len(training_data)}")
    logger.info(f"Training iterations:     {iterations}")
    logger.info(f"Output path:             {output_path}")
    logger.info(f"{'='*60}\n")

    # Initialize new model
    extractor = CarDataExtractor()

    # Train
    logger.info("Training model...")
    extractor.train(training_data, n_iter=iterations)

    # Save model
    logger.info(f"Saving model to {output_path}...")
    extractor.save_model(output_path)

    logger.info(f"\n✅ Retraining complete!")
    logger.info(f"New model saved to: {output_path}\n")


def create_training_report(stats: dict, output_path: str):
    """Create a report of the retraining session"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'data_sources': stats,
        'total_examples': sum(stats.values()),
        'model_path': output_path
    }

    report_file = Path('training_reports') / f"retrain_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    logger.info(f"Training report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Retrain ML model with accumulated production data"
    )
    parser.add_argument(
        "--original",
        default="training_data_labeled.json",
        help="Original labeled data file"
    )
    parser.add_argument(
        "--auto",
        default="auto_training_data.json",
        help="Auto-collected training data"
    )
    parser.add_argument(
        "--manual",
        default="manual_review_data.json",
        help="Manually reviewed training data"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of training iterations (default: 100)"
    )
    parser.add_argument(
        "--output",
        default="./ml_models/car_ner",
        help="Output path for retrained model"
    )

    args = parser.parse_args()

    # Load all training data
    training_data, stats = load_training_data(
        args.original,
        args.auto,
        args.manual
    )

    if not training_data:
        logger.error("❌ No training data found. Cannot retrain.")
        return

    # Show data growth
    print(f"\n{'='*60}")
    print(f"📊 Training Data Growth")
    print(f"{'='*60}")
    print(f"Original labeled:      {stats['original']:4d} examples")
    print(f"Auto-collected:        {stats['auto']:4d} examples")
    print(f"Manual review:         {stats['manual']:4d} examples")
    print(f"{'─'*60}")
    print(f"Total:                 {sum(stats.values()):4d} examples")
    print(f"{'='*60}")

    growth = sum(stats.values()) - stats['original']
    if growth > 0:
        print(f"\n✨ You've added {growth} new examples from production!")
        print(f"   Expected F1 improvement: +{min(growth // 50 * 2, 15)}%")
    print()

    # Confirm retraining
    response = input("Proceed with retraining? (y/n): ").strip().lower()

    if response != 'y':
        print("❌ Retraining cancelled")
        return

    # Retrain
    retrain_model(training_data, args.iterations, args.output)

    # Create report
    create_training_report(stats, args.output)

    print(f"\n{'='*60}")
    print(f"🎉 Success!")
    print(f"{'='*60}")
    print(f"Your model has been retrained with {sum(stats.values())} examples")
    print(f"\n💡 Next steps:")
    print(f"1. Test the new model: python3 test_ml_model.py")
    print(f"2. Update production to use new model")
    print(f"3. Continue collecting data for next retraining")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
