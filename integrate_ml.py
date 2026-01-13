"""
Hybrid Extraction: Regex + ML
==============================

This combines your existing regex patterns with ML for better accuracy.

Strategy:
1. Try regex first (fast, no ML needed)
2. If regex fails, use ML model
3. Log failures for continuous improvement

This is the best approach for production!
"""

import logging
from typing import Optional, Dict
from pathlib import Path

from ml_extractor import CarDataExtractor
import data_scrap

logger = logging.getLogger(__name__)


class HybridCarExtractor:
    """
    Smart extractor that combines regex patterns with ML.

    Falls back to ML when regex fails, giving you the best of both worlds:
    - Speed of regex
    - Flexibility of ML
    """

    def __init__(self, ml_model_path: Optional[str] = "./ml_models/car_ner"):
        """
        Initialize hybrid extractor.

        Args:
            ml_model_path: Path to trained ML model. If doesn't exist, uses regex only.
        """
        self.use_ml = False
        self.ml_extractor = None

        # Try to load ML model
        if ml_model_path and Path(ml_model_path).exists():
            try:
                self.ml_extractor = CarDataExtractor(ml_model_path)
                self.use_ml = True
                logger.info(f"✓ Loaded ML model from {ml_model_path}")
            except Exception as e:
                logger.warning(f"Could not load ML model: {e}")
                logger.info("Will use regex-only extraction")
        else:
            logger.info("ML model not found. Using regex-only extraction")
            logger.info("Train a model with: python train_ml_model.py")

        # Statistics
        self.stats = {
            'total': 0,
            'regex_success': 0,
            'ml_success': 0,
            'failures': 0
        }

    def extract_all(self, description: str, heading: str) -> Dict[str, Optional[int]]:
        """
        Extract car data using hybrid approach.

        Args:
            description: Car description text
            heading: Car heading text

        Returns:
            {mileage, year, power} with extracted values
        """
        self.stats['total'] += 1

        # Phase 1: Try regex (existing code)
        result = {
            'mileage': self._extract_with_regex(description, heading, 'mileage'),
            'year': self._extract_with_regex(description, heading, 'year'),
            'power': self._extract_with_regex(description, heading, 'power')
        }

        # Count regex successes
        regex_found = sum(1 for v in result.values() if v is not None)
        if regex_found == 3:
            self.stats['regex_success'] += 1
            return result

        # Phase 2: ML fallback for missing fields
        if self.use_ml:
            missing_fields = [k for k, v in result.items() if v is None]

            if missing_fields:
                logger.debug(f"Regex failed for {missing_fields}, trying ML...")

                # Combine description and heading for better context
                full_text = f"{heading}. {description}"

                try:
                    ml_result = self.ml_extractor.extract(full_text)

                    # Fill in missing fields
                    ml_filled = 0
                    for field in missing_fields:
                        if field in ml_result and ml_result[field]:
                            result[field] = ml_result[field]
                            ml_filled += 1
                            logger.debug(f"ML filled {field}: {ml_result[field]}")

                    if ml_filled > 0:
                        self.stats['ml_success'] += 1

                except Exception as e:
                    logger.error(f"ML extraction failed: {e}")

        # Check if we still have missing fields
        if None in result.values():
            self.stats['failures'] += 1

        return result

    def _extract_with_regex(self, description: str, heading: str, field: str) -> Optional[int]:
        """Use existing regex functions"""
        # Try description first, then heading
        for text in [description, heading]:
            if field == 'mileage':
                value = data_scrap.get_mileage(text)
            elif field == 'year':
                value = data_scrap.get_year_manufacture(text)
            elif field == 'power':
                value = data_scrap.get_power(text)
            else:
                continue

            if value is not None:
                return value

        return None

    def get_stats(self) -> Dict:
        """Get extraction statistics"""
        if self.stats['total'] == 0:
            return self.stats

        stats = self.stats.copy()
        stats['regex_rate'] = self.stats['regex_success'] / self.stats['total'] * 100
        stats['ml_rate'] = self.stats['ml_success'] / self.stats['total'] * 100
        stats['failure_rate'] = self.stats['failures'] / self.stats['total'] * 100

        return stats

    def print_stats(self):
        """Print extraction statistics"""
        stats = self.get_stats()

        if stats['total'] == 0:
            print("No extractions performed yet")
            return

        print("\n" + "=" * 60)
        print("Hybrid Extractor Statistics")
        print("=" * 60)
        print(f"Total extractions:     {stats['total']}")
        print(f"Regex only:            {stats['regex_success']} ({stats['regex_rate']:.1f}%)")
        print(f"ML helped:             {stats['ml_success']} ({stats['ml_rate']:.1f}%)")
        print(f"Still failed:          {stats['failures']} ({stats['failure_rate']:.1f}%)")
        print("=" * 60 + "\n")


# Example: How to use in your scraper
async def process_data_with_ml(brand: str, url: str, description: str,
                               heading: str, price: int, extractor: HybridCarExtractor) -> Dict:
    """
    Modified version of process_data() that uses hybrid extraction.

    Replace in data_scrap.py:
        result = await process_data(brand, url, description, heading, price)
    With:
        result = await process_data_with_ml(brand, url, description, heading, price, extractor)
    """
    # Use hybrid extractor
    extracted = extractor.extract_all(description, heading)

    # Get model using existing function
    model = data_scrap.get_model(brand=brand, header=heading)

    car_data = {
        "brand": brand,
        "model": model,
        "year_manufacture": extracted['year'],
        "mileage": extracted['mileage'],
        "power": extracted['power'],
        "price": price,
        "heading": heading,
        "url": url
    }

    return car_data


if __name__ == "__main__":
    # Test the hybrid extractor
    logging.basicConfig(level=logging.INFO)

    extractor = HybridCarExtractor()

    # Test cases
    test_cases = [
        {
            "heading": "Škoda Octavia",
            "description": "Prodám Škodu Octavia rok 2015, najeto 120000 km, výkon 110 kW"
        },
        {
            "heading": "BMW X5",
            "description": "BMW X5 2018, 85 tis km, 150kW, benzín, černá"
        },
        {
            "heading": "VW Golf",
            "description": "Golf 2016, pěkný stav, 95000 najetých km, motor 105kW"
        }
    ]

    print("\n🧪 Testing Hybrid Extractor\n")

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}:")
        print(f"  Heading: {test['heading']}")
        print(f"  Description: {test['description']}")

        result = extractor.extract_all(test['description'], test['heading'])

        print(f"  Result: {result}")
        print()

    # Show statistics
    extractor.print_stats()
