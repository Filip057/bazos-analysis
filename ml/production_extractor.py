"""
Production Car Data Extractor
==============================

Combines ML model + context-aware regex for robust extraction.
Implements continuous learning through agreement tracking and review queues.

Features:
- Dual extraction (ML + smart regex)
- Confidence scoring
- Auto-saves high-confidence agreements as training data
- Flags disagreements for manual review
- Statistical monitoring

Usage:
    from production_extractor import ProductionExtractor

    extractor = ProductionExtractor()
    result = extractor.extract(text, car_id='12345')
"""

import json
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime
from collections import Counter

from ml.ml_extractor import CarDataExtractor
from ml.context_aware_patterns import ContextAwarePatterns


class DataNormalizer:
    """Normalizes extracted data for database consistency"""

    # Fuel type normalization
    FUEL_DIESEL = {'diesel', 'nafta', 'tdi', 'td', 'motorová nafta', 'motorova nafta'}
    FUEL_BENZIN = {'benzín', 'benzin', 'gas', 'gasoline', 'b'}
    FUEL_LPG = {'lpg', 'plyn'}
    FUEL_ELECTRIC = {'elektro', 'electric', 'ev', 'elektřina'}

    @staticmethod
    def normalize_fuel(fuel: Optional[str]) -> Optional[str]:
        """Normalize fuel type to standard values"""
        if not fuel:
            return None

        fuel_lower = fuel.lower().strip()

        if fuel_lower in DataNormalizer.FUEL_DIESEL:
            return 'diesel'
        elif fuel_lower in DataNormalizer.FUEL_BENZIN:
            return 'benzín'
        elif fuel_lower in DataNormalizer.FUEL_LPG:
            return 'lpg'
        elif fuel_lower in DataNormalizer.FUEL_ELECTRIC:
            return 'elektro'
        else:
            # Unknown fuel type - return as is
            return fuel

    @staticmethod
    def normalize_mileage(mileage: any) -> Optional[int]:
        """Normalize mileage to integer km"""
        if not mileage:
            return None

        # Already a number
        if isinstance(mileage, (int, float)):
            return int(mileage)

        # String - parse it
        if isinstance(mileage, str):
            import re

            # Remove spaces and convert
            mileage = mileage.replace(' ', '').replace('.', '')

            # Extract just the number
            match = re.search(r'(\d+)', mileage)
            if match:
                value = int(match.group(1))

                # Check for thousands abbreviations
                if re.search(r'\d+\s*(?:tis|t)\.?\s*km', mileage, re.IGNORECASE):
                    value = value * 1000

                return value

        return None

    @staticmethod
    def normalize_power(power: any) -> Optional[int]:
        """Normalize power to integer kW"""
        if not power:
            return None

        # Already a number
        if isinstance(power, (int, float)):
            return int(power)

        # String - parse it
        if isinstance(power, str):
            import re
            # Extract just the number
            match = re.search(r'(\d+)', power)
            if match:
                return int(match.group(1))

        return None

    @staticmethod
    def normalize_year(year: any) -> Optional[int]:
        """Normalize year to integer"""
        if not year:
            return None

        # Already a number
        if isinstance(year, (int, float)):
            return int(year)

        # String - parse it
        if isinstance(year, str):
            import re
            match = re.search(r'(\d{4})', year)
            if match:
                return int(match.group(1))

        return None


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionExtractor:
    """Production-ready extractor with continuous learning"""

    def __init__(self,
                 ml_model_path: str = './ml_models/car_ner',
                 auto_training_file: str = 'auto_training_data.json',
                 review_queue_file: str = 'review_queue.json',
                 stats_file: str = 'extraction_stats.json'):

        # Load ML model
        self.ml_extractor = CarDataExtractor(ml_model_path)

        # Load context-aware regex
        self.regex_patterns = ContextAwarePatterns()

        # Files for continuous learning
        self.auto_training_file = Path(auto_training_file)
        self.review_queue_file = Path(review_queue_file)
        self.stats_file = Path(stats_file)

        # In-memory queues
        self.auto_training_queue = []
        self.review_queue = []

        # Statistics
        self.stats = {
            'total_extractions': 0,
            'full_agreements': 0,
            'partial_agreements': 0,
            'disagreements': 0,
            'ml_only': 0,
            'regex_only': 0,
            'both_empty': 0,
            'field_stats': {
                'mileage': {'agree': 0, 'disagree': 0},
                'year': {'agree': 0, 'disagree': 0},
                'power': {'agree': 0, 'disagree': 0},
                'fuel': {'agree': 0, 'disagree': 0}
            }
        }

        logger.info("Production extractor initialized")

    def extract(self, text: str, car_id: Optional[str] = None) -> Dict:
        """
        Extract car data using ML + regex with disagreement detection

        Returns:
            {
                'mileage': int or None,
                'year': int or None,
                'power': int or None,
                'fuel': str or None,
                'confidence': 'high' | 'medium' | 'low',
                'agreement': True/False,
                'flagged_for_review': True/False
            }
        """
        self.stats['total_extractions'] += 1

        # 1. ML Extraction (raw)
        ml_result_raw = self.ml_extractor.extract(text)

        # 2. Context-aware regex extraction (raw)
        regex_result_raw = self._extract_with_regex(text)

        # 3. NORMALIZE BOTH before comparison (fixes benzín vs benzin issue)
        normalizer = DataNormalizer()
        ml_result = self._normalize_result(ml_result_raw, normalizer)
        regex_result = self._normalize_result(regex_result_raw, normalizer)

        # 4. Compare NORMALIZED results (benzín == benzín now!)
        comparison = self._compare_results(ml_result, regex_result)

        # 5. Make decision based on comparison
        final_result, confidence = self._decide_final_result(
            ml_result,
            regex_result,
            comparison
        )

        # 5. Handle based on agreement level
        if comparison['agreement_level'] == 'full':
            # High confidence - auto-add to training data
            self._add_to_auto_training(text, final_result, car_id)
            self.stats['full_agreements'] += 1

        elif comparison['agreement_level'] == 'partial':
            # Medium confidence - log but don't flag
            self.stats['partial_agreements'] += 1
            logger.debug(f"Partial agreement on car {car_id}: {comparison['disagreements']}")

        elif comparison['agreement_level'] == 'none':
            # Low confidence - flag for review
            self._add_to_review_queue(text, ml_result, regex_result, car_id, comparison)
            self.stats['disagreements'] += 1

        # 6. Update field statistics
        self._update_field_stats(comparison)

        # 7. Prepare response (already normalized in step 3)
        response = {
            **final_result,  # Already normalized
            'confidence': confidence,
            'agreement': comparison['agreement_level'],
            'flagged_for_review': comparison['agreement_level'] == 'none',
            'car_id': car_id,
            # Include raw values for debugging
            'raw_values': ml_result_raw if logger.isEnabledFor(logging.DEBUG) else None
        }

        return response

    def _extract_with_regex(self, text: str) -> Dict:
        """Extract using context-aware regex patterns"""
        result = {
            'mileage': None,
            'year': None,
            'power': None,
            'fuel': None
        }

        # Mileage
        mileage_matches = self.regex_patterns.find_mileage(text)
        if mileage_matches:
            # Take highest confidence match
            best_match = max(mileage_matches,
                           key=lambda m: {'high': 3, 'medium': 2, 'low': 1}[m.confidence])
            result['mileage'] = best_match.value

        # Year
        year_matches = self.regex_patterns.find_years(text)
        if year_matches:
            best_match = max(year_matches,
                           key=lambda m: {'high': 3, 'medium': 2, 'low': 1}[m.confidence])
            result['year'] = best_match.value

        # Power
        power_matches = self.regex_patterns.find_power(text)
        if power_matches:
            best_match = max(power_matches,
                           key=lambda m: {'high': 3, 'medium': 2, 'low': 1}[m.confidence])
            result['power'] = best_match.value

        # Fuel - normalize to base form
        # TODO: Add fuel extraction to context_aware_patterns.py
        # For now, use simple pattern
        import re
        fuel_pattern = re.compile(r'\b(benzin|benzín|nafta|diesel|dýzl|naftak|turbodiesel|tdi|tsi|hybrid|elektro|electric|lpg|cng|plyn)\b', re.IGNORECASE)
        fuel_match = fuel_pattern.search(text)
        if fuel_match:
            fuel = fuel_match.group(1).lower()
            # Normalize
            if fuel in ['diesel', 'nafta', 'tdi', 'turbodiesel', 'dýzl', 'naftak']:
                result['fuel'] = 'diesel'
            elif fuel in ['benzin', 'benzín', 'tsi']:
                result['fuel'] = 'benzin'
            else:
                result['fuel'] = fuel

        return result

    def _normalize_result(self, result: Dict, normalizer: DataNormalizer) -> Dict:
        """Normalize extraction result for consistent comparison"""
        return {
            'mileage': normalizer.normalize_mileage(result.get('mileage')),
            'year': normalizer.normalize_year(result.get('year')),
            'power': normalizer.normalize_power(result.get('power')),
            'fuel': normalizer.normalize_fuel(result.get('fuel'))
        }

    def _compare_results(self, ml_result: Dict, regex_result: Dict) -> Dict:
        """Compare ML and regex results field by field"""
        comparison = {
            'agreements': [],
            'disagreements': [],
            'ml_only': [],
            'regex_only': [],
            'both_empty': [],
            'agreement_level': None
        }

        for field in ['mileage', 'year', 'power', 'fuel']:
            ml_val = ml_result.get(field)
            regex_val = regex_result.get(field)

            if ml_val is not None and regex_val is not None:
                if ml_val == regex_val:
                    comparison['agreements'].append(field)
                else:
                    comparison['disagreements'].append(field)
            elif ml_val is not None and regex_val is None:
                comparison['ml_only'].append(field)
            elif ml_val is None and regex_val is not None:
                comparison['regex_only'].append(field)
            else:
                comparison['both_empty'].append(field)

        # Determine agreement level
        total_fields = 4
        agreed_fields = len(comparison['agreements'])

        if agreed_fields == total_fields:
            comparison['agreement_level'] = 'full'
        elif agreed_fields >= 2:
            comparison['agreement_level'] = 'partial'
        else:
            comparison['agreement_level'] = 'none'

        return comparison

    def _decide_final_result(self, ml_result: Dict, regex_result: Dict,
                            comparison: Dict) -> tuple:
        """Decide final values based on comparison"""
        final = {}

        for field in ['mileage', 'year', 'power', 'fuel']:
            if field in comparison['agreements']:
                # Both agree - high confidence
                final[field] = ml_result[field]
            elif field in comparison['disagreements']:
                # Disagree - prefer regex (more conservative)
                final[field] = regex_result[field]
                logger.debug(f"Disagreement on {field}: ML={ml_result[field]}, Regex={regex_result[field]} - Using regex")
            elif field in comparison['ml_only']:
                # Only ML found - trust ML (it's smarter)
                final[field] = ml_result[field]
            elif field in comparison['regex_only']:
                # Only regex found - trust regex
                final[field] = regex_result[field]
            else:
                # Both empty
                final[field] = None

        # Determine confidence
        if comparison['agreement_level'] == 'full':
            confidence = 'high'
        elif comparison['agreement_level'] == 'partial':
            confidence = 'medium'
        else:
            confidence = 'low'

        return final, confidence

    def _add_to_auto_training(self, text: str, result: Dict, car_id: Optional[str]):
        """Add high-confidence extraction to auto-training queue"""
        # Convert to spaCy training format
        entities = []

        # Find entities in text (approximate positions)
        # This is simplified - in production you'd want exact positions
        if result['mileage']:
            # Find mileage in text
            import re
            patterns = [
                r'\d{1,3}(?:\s?\d{3})*\s?km',
                r'\d{1,3}\s?(?:tis|t)\s?km'
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities.append((match.start(), match.end(), 'MILEAGE'))
                    break

        if result['year']:
            # Find year in text
            year_str = str(result['year'])
            pos = text.find(year_str)
            if pos != -1:
                entities.append((pos, pos + 4, 'YEAR'))

        if result['power']:
            # Find power in text
            import re
            pattern = rf"{result['power']}\s?(?:kw|ps|koní)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append((match.start(), match.end(), 'POWER'))

        if result['fuel']:
            # Find fuel in text
            pos = text.lower().find(result['fuel'].lower())
            if pos != -1:
                entities.append((pos, pos + len(result['fuel']), 'FUEL'))

        training_example = (text, {'entities': entities})
        self.auto_training_queue.append({
            'data': training_example,
            'car_id': car_id,
            'timestamp': datetime.now().isoformat(),
            'confidence': 'high',
            'source': 'auto_agreement'
        })

    def _add_to_review_queue(self, text: str, ml_result: Dict, regex_result: Dict,
                            car_id: Optional[str], comparison: Dict):
        """Add disagreement to review queue"""
        self.review_queue.append({
            'car_id': car_id,
            'text': text[:500],  # First 500 chars for review
            'ml_result': ml_result,
            'regex_result': regex_result,
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        })

    def _update_field_stats(self, comparison: Dict):
        """Update field-level statistics"""
        for field in ['mileage', 'year', 'power', 'fuel']:
            if field in comparison['agreements']:
                self.stats['field_stats'][field]['agree'] += 1
            elif field in comparison['disagreements']:
                self.stats['field_stats'][field]['disagree'] += 1

    def save_queues(self):
        """Save auto-training and review queues to disk"""
        # Save auto-training data
        if self.auto_training_queue:
            existing = []
            if self.auto_training_file.exists():
                with open(self.auto_training_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)

            existing.extend(self.auto_training_queue)

            with open(self.auto_training_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(self.auto_training_queue)} examples to {self.auto_training_file}")
            self.auto_training_queue = []

        # Save review queue
        if self.review_queue:
            existing = []
            if self.review_queue_file.exists():
                with open(self.review_queue_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)

            existing.extend(self.review_queue)

            with open(self.review_queue_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(self.review_queue)} items to review queue")
            self.review_queue = []

        # Save statistics
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)

    def print_stats(self):
        """Print extraction statistics"""
        total = self.stats['total_extractions']
        if total == 0:
            print("No extractions yet")
            return

        print(f"\n{'='*60}")
        print(f"Production Extraction Statistics")
        print(f"{'='*60}")
        print(f"Total extractions:     {total}")
        print(f"Full agreements:       {self.stats['full_agreements']} ({self.stats['full_agreements']/total*100:.1f}%)")
        print(f"Partial agreements:    {self.stats['partial_agreements']} ({self.stats['partial_agreements']/total*100:.1f}%)")
        print(f"Disagreements:         {self.stats['disagreements']} ({self.stats['disagreements']/total*100:.1f}%)")
        print(f"{'='*60}")
        print(f"\nField-level accuracy:")
        for field, stats in self.stats['field_stats'].items():
            total_field = stats['agree'] + stats['disagree']
            if total_field > 0:
                accuracy = stats['agree'] / total_field * 100
                print(f"  {field:10s}: {accuracy:5.1f}% agreement ({stats['agree']}/{total_field})")
        print(f"{'='*60}\n")


# Example usage
if __name__ == "__main__":
    # Initialize extractor
    extractor = ProductionExtractor()

    # Test examples
    test_texts = [
        "Škoda Octavia 2015, STK do 2027, najeto 150000 km, výkon 110 kW, diesel",
        "BMW 2018, 85 tis km, 150kW, benzín",
        "VW Golf rok výroby 2016, 95000 km, motor 105 kW"
    ]

    print("Testing production extractor:\n")

    for i, text in enumerate(test_texts, 1):
        print(f"Example {i}:")
        print(f"Text: {text}\n")

        result = extractor.extract(text, car_id=f"test_{i}")

        print(f"Result:")
        print(f"  Mileage: {result['mileage']}")
        print(f"  Year: {result['year']}")
        print(f"  Power: {result['power']}")
        print(f"  Fuel: {result['fuel']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Agreement: {result['agreement']}")
        print(f"  Flagged for review: {result['flagged_for_review']}")
        print()

    # Save queues
    extractor.save_queues()

    # Print statistics
    extractor.print_stats()
