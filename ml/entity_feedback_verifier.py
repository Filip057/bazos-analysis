"""
Generic Entity Feedback Verification System
============================================

Extends the feedback verification pattern to ANY entity type:
  - power (kW)
  - mileage (km)
  - fuel (diesel, benzín, etc.)

Triggered when: ML entity = None, Regex entity = found

How it works:
  1. Regex finds candidate (e.g., "145 kW")
  2. Extract context window around candidate
  3. Ask ML: "is there a {entity_type} in this context?"
  4. Combine regex confidence + ML confirmation → final confidence

This is a generalized version of YearFeedbackVerifier.
"""

import re
from typing import Optional, Callable, Any
from dataclasses import dataclass, asdict


@dataclass
class EntityVerification:
    """
    Generic verification result for any entity type.

    Fields:
    - entity_type: 'power', 'mileage', or 'fuel'
    - candidate_value: The regex-found value (e.g., "145 kW", "90000 km")
    - regex_confidence: Regex confidence level ('high', 'medium', 'low')
    - ml_confirmed: Did ML find the same entity in the context window?
    - confidence: Final combined confidence score (0.0-1.0)
    - verified: True if confidence >= threshold
    - method: Description of how the decision was made
    - context_text: The context window shown to ML
    """
    entity_type: str
    candidate_value: str
    regex_confidence: str
    ml_confirmed: bool
    confidence: float
    verified: bool
    method: str
    context_text: str

    def to_dict(self) -> dict:
        return asdict(self)


class EntityFeedbackVerifier:
    """
    Generic feedback verifier for power, mileage, and fuel entities.

    Only triggered when: ML = None, Regex = found value

    Configuration for each entity type:
    - Validation rules (valid range, format checks)
    - Value extraction/comparison logic
    - Confidence threshold

    Example:
        verifier = EntityFeedbackVerifier(ml_extractor)

        # Power verification
        result = verifier.verify(
            text="Škoda Octavia 145 kW diesel",
            entity_type='power',
            regex_candidate="145 kW",
            regex_confidence='medium'
        )

        if result.verified:
            power = result.candidate_value
    """

    # Configuration for each entity type
    ENTITY_CONFIGS = {
        'power': {
            'valid_range': (30, 500),  # kW
            'extract_numeric': lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else None,
            'confidence_threshold': 0.65,
            'context_window': 60
        },
        'mileage': {
            'valid_range': (0, 1000000),  # km
            'extract_numeric': lambda x: int(re.sub(r'\D', '', x)) if re.search(r'\d', x) else None,
            'confidence_threshold': 0.65,
            'context_window': 60
        },
        'fuel': {
            'valid_values': ['diesel', 'benzín', 'lpg', 'elektro', 'benzin', 'nafta', 'plyn'],
            'normalize': lambda x: x.lower().strip(),
            'confidence_threshold': 0.65,
            'context_window': 60
        }
    }

    # Default confidence threshold
    DEFAULT_CONFIDENCE_THRESHOLD = 0.65
    DEFAULT_CONTEXT_WINDOW = 60

    def __init__(self, ml_extractor, confidence_threshold: Optional[float] = None):
        """
        Args:
            ml_extractor: CarDataExtractor instance (already loaded)
            confidence_threshold: Override default threshold for all entities
        """
        self.ml_extractor = ml_extractor
        self.confidence_threshold = confidence_threshold or self.DEFAULT_CONFIDENCE_THRESHOLD

    def verify(
        self,
        text: str,
        entity_type: str,
        regex_candidate: str,
        regex_confidence: str = 'low'
    ) -> EntityVerification:
        """
        Verify if a regex-found entity is genuine.

        Args:
            text: Original car listing text
            entity_type: Type of entity ('power', 'mileage', 'fuel')
            regex_candidate: Value found by regex (e.g., "145 kW")
            regex_confidence: Regex confidence level ('high', 'medium', 'low')

        Returns:
            EntityVerification with confidence score and metadata
        """
        if entity_type not in self.ENTITY_CONFIGS:
            raise ValueError(f"Unsupported entity_type: {entity_type}. Must be one of {list(self.ENTITY_CONFIGS.keys())}")

        config = self.ENTITY_CONFIGS[entity_type]

        # 1. Basic validation
        is_valid = self._validate_entity(regex_candidate, entity_type, config)
        if not is_valid:
            return EntityVerification(
                entity_type=entity_type,
                candidate_value=regex_candidate,
                regex_confidence=regex_confidence,
                ml_confirmed=False,
                confidence=0.0,
                verified=False,
                method=f"REJECTED_INVALID_{entity_type.upper()}",
                context_text=""
            )

        # 2. Extract context window
        context_window_size = config.get('context_window', self.DEFAULT_CONTEXT_WINDOW)
        context_text = self._extract_context(text, regex_candidate, context_window_size)

        # 3. Ask ML to verify
        ml_confirmed = self._ask_ml_to_verify(context_text, regex_candidate, entity_type, config)

        # 4. Calculate final confidence
        threshold = config.get('confidence_threshold', self.confidence_threshold)
        confidence, method = self._calculate_confidence(regex_confidence, ml_confirmed, entity_type)

        return EntityVerification(
            entity_type=entity_type,
            candidate_value=regex_candidate,
            regex_confidence=regex_confidence,
            ml_confirmed=ml_confirmed,
            confidence=confidence,
            verified=confidence >= threshold,
            method=method,
            context_text=context_text
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_entity(self, candidate: str, entity_type: str, config: dict) -> bool:
        """Validate if the candidate is a plausible value for this entity type."""
        if entity_type in ['power', 'mileage']:
            # Numeric validation with valid range
            extract_fn = config['extract_numeric']
            try:
                value = extract_fn(candidate)
                if value is None:
                    return False
                min_val, max_val = config['valid_range']
                return min_val <= value <= max_val
            except Exception:
                return False

        elif entity_type == 'fuel':
            # Text validation - check if it's a known fuel type
            normalize_fn = config.get('normalize', lambda x: x)
            normalized = normalize_fn(candidate)
            valid_values = config['valid_values']
            return any(v in normalized for v in valid_values)

        return False

    def _extract_context(self, text: str, candidate: str, window_size: int) -> str:
        """Extract a context window around the candidate value."""
        pos = text.find(candidate)
        if pos == -1:
            pos = text.lower().find(candidate.lower())
        if pos == -1:
            return text  # Can't find it, return full text

        start = max(0, pos - window_size)
        end = min(len(text), pos + len(candidate) + window_size)
        return text[start:end]

    def _ask_ml_to_verify(
        self,
        context_text: str,
        candidate: str,
        entity_type: str,
        config: dict
    ) -> bool:
        """
        Run ML on the context window and check if it finds the same entity.

        Returns True if ML confirmed the candidate.
        """
        try:
            ml_result = self.ml_extractor.extract(context_text)
            ml_value = ml_result.get(entity_type)

            if ml_value is None:
                return False

            # Compare values based on entity type
            if entity_type in ['power', 'mileage']:
                # Numeric comparison
                extract_fn = config['extract_numeric']
                candidate_num = extract_fn(candidate)
                ml_num = extract_fn(ml_value)
                return candidate_num is not None and ml_num is not None and candidate_num == ml_num

            elif entity_type == 'fuel':
                # Text comparison (case-insensitive, normalized)
                normalize_fn = config.get('normalize', lambda x: x)
                return normalize_fn(candidate) == normalize_fn(ml_value)

            return False

        except Exception:
            return False

    def _calculate_confidence(
        self,
        regex_confidence: str,
        ml_confirmed: bool,
        entity_type: str
    ) -> tuple:
        """
        Calculate final confidence based on regex confidence and ML confirmation.

        Same confidence matrix as YearFeedbackVerifier.

        Returns: (confidence: float, method: str)
        """
        entity_upper = entity_type.upper()

        if regex_confidence == 'high' and ml_confirmed:
            return 0.95, f"ML_CONFIRMED_HIGH_REGEX_{entity_upper}"

        if regex_confidence == 'high' and not ml_confirmed:
            # High regex confidence (e.g., "výkon 145 kW") is reliable
            return 0.80, f"HIGH_REGEX_ACCEPTED_{entity_upper}"

        if regex_confidence == 'medium' and ml_confirmed:
            return 0.85, f"ML_CONFIRMED_MEDIUM_REGEX_{entity_upper}"

        if regex_confidence == 'medium' and not ml_confirmed:
            return 0.55, f"MEDIUM_REGEX_UNCERTAIN_{entity_upper}"

        if regex_confidence == 'low' and ml_confirmed:
            return 0.70, f"ML_CONFIRMED_LOW_REGEX_{entity_upper}"

        # low regex, ML doesn't confirm → not trustworthy
        return 0.30, f"REGEX_ONLY_UNVERIFIED_{entity_upper}"
