"""
ML Model Training Script
========================

This script trains your car data extraction model.

Workflow:
1. Load labeled training data
2. Split into train/test sets
3. Train the model
4. Evaluate performance
5. Save the trained model

Usage:
    python train_ml_model.py --data training_data.json --iterations 30
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import random

from ml.ml_extractor import CarDataExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_training_data(json_path: str) -> List[Tuple[str, Dict]]:
    """Load labeled data from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} training examples")
    return data


def split_train_test(data: List[Tuple[str, Dict]],
                      test_split: float = 0.2) -> Tuple[List, List]:
    """
    Split data into training and testing sets.

    This is important in ML to evaluate how well the model works
    on data it hasn't seen before.

    Args:
        data: Full dataset
        test_split: Fraction to use for testing (e.g., 0.2 = 20%)

    Returns:
        (train_data, test_data)
    """
    random.shuffle(data)
    split_idx = int(len(data) * (1 - test_split))

    train_data = data[:split_idx]
    test_data = data[split_idx:]

    logger.info(f"Split: {len(train_data)} training, {len(test_data)} testing")
    return train_data, test_data


def analyze_training_data(data: List[Tuple[str, Dict]]):
    """
    Analyze the training data to understand what we're working with.
    This helps catch labeling errors.
    """
    total_entities = 0
    entity_counts = {}

    for text, annotations in data:
        entities = annotations.get("entities", [])
        total_entities += len(entities)

        for start, end, label in entities:
            entity_counts[label] = entity_counts.get(label, 0) + 1

            # Validate entity positions
            if start >= end or end > len(text):
                logger.warning(f"Invalid entity in: '{text}'")

    logger.info(f"\n{'='*60}")
    logger.info(f"Training Data Analysis:")
    logger.info(f"  Total examples: {len(data)}")
    logger.info(f"  Total entities: {total_entities}")
    logger.info(f"  Average entities per example: {total_entities/len(data):.1f}")
    logger.info(f"\nEntity distribution:")
    for label, count in sorted(entity_counts.items()):
        logger.info(f"  {label}: {count} ({count/len(data):.1f} per example)")
    logger.info(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Train ML model for car data extraction"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to labeled training data (JSON file)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="Number of training iterations (default: 30)"
    )
    parser.add_argument(
        "--test-split",
        type=float,
        default=0.2,
        help="Fraction of data to use for testing (default: 0.2)"
    )
    parser.add_argument(
        "--output",
        default="./ml_models/car_ner",
        help="Output directory for trained model"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze training data quality, don't train"
    )
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Only evaluate existing model, don't train"
    )

    args = parser.parse_args()

    # Load data
    logger.info(f"Loading training data from {args.data}")
    training_data = load_training_data(args.data)

    if len(training_data) < 10:
        logger.error(f"⚠️  Only {len(training_data)} examples found!")
        logger.error(f"   You need at least 50-100 for a good model.")
        logger.error(f"   Use label_data.py to create more training data.")
        return

    # Analyze data
    analyze_training_data(training_data)

    # If analyze-only, stop here
    if args.analyze_only:
        logger.info("\n✅ Analysis complete!")
        logger.info("\n💡 Data looks good? Train with:")
        logger.info(f"   python3 -m ml.train_ml_model --data {args.data} --iterations {args.iterations}")
        return

    # Split into train/test
    train_data, test_data = split_train_test(training_data, args.test_split)

    # If evaluate-only, load existing model and evaluate
    if args.evaluate_only:
        logger.info("\n📊 Evaluating existing model...")

        # Check if model exists
        if not Path(args.output).exists():
            logger.error(f"❌ Model not found at {args.output}")
            logger.error("   Train a model first!")
            return

        # Load existing model
        extractor = CarDataExtractor(args.output)

        if test_data:
            scores = extractor.evaluate(test_data)

            logger.info(f"\n{'='*60}")
            logger.info(f"Model Performance:")
            logger.info(f"  Precision: {scores['precision']:.1%} (how many predictions were correct)")
            logger.info(f"  Recall:    {scores['recall']:.1%} (how many entities were found)")
            logger.info(f"  F1 Score:  {scores['f1']:.1%} (overall accuracy)")
            logger.info(f"{'='*60}\n")

            if scores['f1'] < 0.7:
                logger.warning("⚠️  Model F1 score is below 70%")
                logger.warning("   Try adding more training data or retraining")
            elif scores['f1'] >= 0.8:
                logger.info("✅ Excellent! F1 score is 80%+ ")
        else:
            logger.error("❌ No test data available for evaluation")

        logger.info("\n✅ Evaluation complete!")
        return

    # Continue with training...

    if len(test_data) == 0:
        logger.warning("Not enough data for test set. Using all for training.")
        train_data = training_data
        test_data = None

    # Initialize extractor
    logger.info("Initializing ML model...")
    extractor = CarDataExtractor()

    # Train the model
    logger.info(f"\n🎓 Training model with {args.iterations} iterations...")
    logger.info(f"This will take a few minutes. Watch the loss decrease!\n")

    extractor.train(
        training_data=train_data,
        n_iter=args.iterations,
        output_dir=args.output
    )

    # Evaluate on test set
    if test_data:
        logger.info("\n📊 Evaluating model on test set...")
        scores = extractor.evaluate(test_data)

        logger.info(f"\n{'='*60}")
        logger.info(f"Model Performance:")
        logger.info(f"  Precision: {scores['precision']:.1%} (how many predictions were correct)")
        logger.info(f"  Recall:    {scores['recall']:.1%} (how many entities were found)")
        logger.info(f"  F1 Score:  {scores['f1']:.1%} (overall accuracy)")
        logger.info(f"{'='*60}\n")

        if scores['f1'] < 0.7:
            logger.warning("⚠️  Model F1 score is below 70%")
            logger.warning("   Try adding more training data or training longer")

    # Test on example texts
    logger.info("\n🧪 Testing on example texts:")

    example_texts = [
        "Škoda Octavia 2015, najeto 120000 km, výkon 110 kW",
        "BMW 2018, 85 tis km, 150kW",
        "Prodám VW Golf rok 2016, 95000 km, motor 105 kW"
    ]

    for text in example_texts:
        result = extractor.extract(text)
        logger.info(f"\n  Text: {text}")
        logger.info(f"  Extracted: {result}")

    logger.info(f"\n\n✅ Training complete!")
    logger.info(f"📁 Model saved to: {args.output}")
    logger.info(f"\n💡 Next steps:")
    logger.info(f"   1. Test the model: python test_ml_model.py")
    logger.info(f"   2. Integrate with scraper: See integrate_ml.py")


if __name__ == "__main__":
    main()
