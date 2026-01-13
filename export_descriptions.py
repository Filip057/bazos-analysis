"""
Export Car Descriptions for Labeling
====================================

This extracts car descriptions from your scraped data
so you can label them for ML training.

Usage:
    python export_descriptions.py --output descriptions.txt --limit 100
"""

import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.model import Car
from config import get_config
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_descriptions(output_file: str, limit: int = 100, random_sample: bool = True):
    """
    Export car descriptions to a text file.

    Args:
        output_file: Where to save descriptions
        limit: How many descriptions to export
        random_sample: If True, randomly sample from database
    """
    # Connect to database
    config = get_config()
    engine = create_engine(config.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Query cars from database
        query = session.query(Car)

        if random_sample:
            # Get total count
            total = query.count()
            if total == 0:
                logger.error("No cars in database! Run the scraper first.")
                return

            # Random sample
            logger.info(f"Found {total} cars in database")
            offset = random.randint(0, max(0, total - limit))
            cars = query.offset(offset).limit(limit).all()
        else:
            cars = query.limit(limit).all()

        if not cars:
            logger.error("No cars found!")
            return

        # Create combined text (heading + brand + model + other info)
        descriptions = []
        for car in cars:
            # Combine available information into one text
            parts = []

            if car.brand:
                parts.append(car.brand.capitalize())
            if car.model:
                parts.append(car.model.capitalize())
            if car.year_manufacture:
                parts.append(f"rok {car.year_manufacture}")
            if car.mileage:
                parts.append(f"{car.mileage} km")
            if car.power:
                parts.append(f"{car.power} kW")

            # Combine into one line
            description = ", ".join(parts)

            if description:
                descriptions.append(description)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            for desc in descriptions:
                f.write(desc + '\n')

        logger.info(f"\n✓ Exported {len(descriptions)} descriptions to {output_file}")
        logger.info(f"\nNext steps:")
        logger.info(f"  1. Label the data:")
        logger.info(f"     python label_data.py --input {output_file} --output training_data.json --limit 50")
        logger.info(f"\n  2. Train the model:")
        logger.info(f"     python train_ml_model.py --data training_data.json")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export car descriptions for ML training data"
    )
    parser.add_argument(
        "--output",
        default="descriptions.txt",
        help="Output text file"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of descriptions to export (default: 100)"
    )
    parser.add_argument(
        "--no-random",
        action="store_true",
        help="Don't use random sampling (take first N)"
    )

    args = parser.parse_args()

    export_descriptions(
        output_file=args.output,
        limit=args.limit,
        random_sample=not args.no_random
    )


if __name__ == "__main__":
    main()
