"""
Mileage Resolution System

This module handles comparison and resolution of mileage values extracted
from both ML and regex methods. It provides:
- Preservation of raw extraction values
- Normalization for comparison
- Disagreement detection and classification
- Intelligent resolution with confidence scoring
"""

import re
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass, asdict


DisagreementType = Literal["NONE", "MINOR_FORMATTING", "MAJOR"]
ResolutionMethod = Literal["AUTO_NORMALIZED", "MANUAL", "ML_PREFERRED", "REGEX_PREFERRED"]


@dataclass
class MileageResolution:
    """
    Complete mileage resolution result with metadata.

    Structure:
    - ml_raw: Never modified, keeps original ML extraction
    - regex_raw: Never modified, keeps original regex extraction
    - normalized_ml: Normalized version for comparison
    - normalized_regex: Normalized version for comparison
    - disagreement_type: Classification of disagreement level
    - resolved_value: Final value to use
    - resolution_method: How the value was resolved
    - confidence: Confidence score (0.0-1.0)
    """
    ml_raw: Optional[str]
    regex_raw: Optional[str]
    normalized_ml: Optional[str]
    normalized_regex: Optional[str]
    disagreement_type: DisagreementType
    resolved_value: Optional[str]
    resolution_method: ResolutionMethod
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return asdict(self)


class MileageNormalizer:
    """Handles normalization of mileage values for comparison."""

    # Standard units we support
    UNITS = {
        'km': 'km',
        'kilometer': 'km',
        'kilometers': 'km',
        'kilometre': 'km',
        'kilometres': 'km',
        'mi': 'mi',
        'mile': 'mi',
        'miles': 'mi',
    }

    @staticmethod
    def normalize(raw_value: Optional[str]) -> Optional[str]:
        """
        Normalize mileage value to standard format: "{number}km"

        Examples:
        - "90000 km" -> "90000km"
        - "90000Km" -> "90000km"
        - "90 000 km" -> "90000km"
        - "150000 KM" -> "150000km"
        - "50000 mi" -> "50000mi"

        Returns None if value cannot be normalized.
        """
        if not raw_value or not isinstance(raw_value, str):
            return None

        # Clean and lowercase
        cleaned = raw_value.strip().lower()

        # Remove spaces between digits (handles "90 000 km" -> "90000km")
        cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)

        # Extract number and unit
        match = re.match(r'(\d+)\s*([a-z]+)', cleaned)
        if not match:
            return None

        number = match.group(1)
        unit = match.group(2)

        # Normalize unit
        normalized_unit = MileageNormalizer.UNITS.get(unit)
        if not normalized_unit:
            return None

        return f"{number}{normalized_unit}"

    @staticmethod
    def extract_numeric(raw_value: Optional[str]) -> Optional[int]:
        """Extract numeric value from mileage string."""
        if not raw_value or not isinstance(raw_value, str):
            return None

        # Remove spaces between digits first
        cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', raw_value)
        match = re.search(r'(\d+)', cleaned)
        return int(match.group(1)) if match else None


class MileageResolver:
    """
    Resolves disagreements between ML and regex mileage extractions.

    Resolution strategy:
    1. If both agree (after normalization) -> HIGH confidence
    2. If minor formatting difference -> AUTO_NORMALIZED, HIGH confidence
    3. If major disagreement -> Use ML (user preference), MEDIUM confidence
    4. If only one source available -> Use it, MEDIUM confidence
    5. If neither available -> None, LOW confidence
    """

    def __init__(self, prefer_ml: bool = True):
        """
        Initialize resolver.

        Args:
            prefer_ml: If True, prefer ML in case of disagreement (default: True, prefer ML)
        """
        self.prefer_ml = prefer_ml
        self.normalizer = MileageNormalizer()

    def resolve(
        self,
        ml_raw: Optional[str],
        regex_raw: Optional[str],
        manual_override: Optional[str] = None
    ) -> MileageResolution:
        """
        Resolve mileage value from ML and regex extractions.

        Args:
            ml_raw: Raw mileage value from ML extraction
            regex_raw: Raw mileage value from regex extraction
            manual_override: Optional manual value (takes precedence)

        Returns:
            MileageResolution object with complete resolution metadata
        """
        # Handle manual override
        if manual_override is not None:
            return MileageResolution(
                ml_raw=ml_raw,
                regex_raw=regex_raw,
                normalized_ml=self.normalizer.normalize(ml_raw),
                normalized_regex=self.normalizer.normalize(regex_raw),
                disagreement_type="NONE",  # Manual override bypasses disagreement
                resolved_value=manual_override,
                resolution_method="MANUAL",
                confidence=1.0
            )

        # Normalize both values
        normalized_ml = self.normalizer.normalize(ml_raw)
        normalized_regex = self.normalizer.normalize(regex_raw)

        # Classify disagreement
        disagreement_type = self._classify_disagreement(
            normalized_ml, normalized_regex
        )

        # Resolve based on disagreement type
        resolution = self._resolve_disagreement(
            ml_raw=ml_raw,
            regex_raw=regex_raw,
            normalized_ml=normalized_ml,
            normalized_regex=normalized_regex,
            disagreement_type=disagreement_type
        )

        return MileageResolution(
            ml_raw=ml_raw,
            regex_raw=regex_raw,
            normalized_ml=normalized_ml,
            normalized_regex=normalized_regex,
            disagreement_type=disagreement_type,
            resolved_value=resolution['value'],
            resolution_method=resolution['method'],
            confidence=resolution['confidence']
        )

    def _classify_disagreement(
        self,
        normalized_ml: Optional[str],
        normalized_regex: Optional[str]
    ) -> DisagreementType:
        """
        Classify the type of disagreement between ML and regex extractions.

        Returns:
            - "NONE": Both agree (or both missing)
            - "MINOR_FORMATTING": Same value, different formatting
            - "MAJOR": Different values or units
        """
        # Both missing
        if normalized_ml is None and normalized_regex is None:
            return "NONE"

        # Both present
        if normalized_ml is not None and normalized_regex is not None:
            if normalized_ml == normalized_regex:
                return "NONE"

            # Check if only formatting differs
            # Extract numeric parts to see if the disagreement is just about units
            ml_num = self.normalizer.extract_numeric(normalized_ml)
            regex_num = self.normalizer.extract_numeric(normalized_regex)

            if ml_num == regex_num:
                # Same number, different units (or formatting edge case)
                return "MINOR_FORMATTING"
            else:
                # Different numbers
                return "MAJOR"

        # One missing - not a disagreement per se, but we flag it as minor
        # (one method found something, the other didn't)
        return "MINOR_FORMATTING"

    def _resolve_disagreement(
        self,
        ml_raw: Optional[str],
        regex_raw: Optional[str],
        normalized_ml: Optional[str],
        normalized_regex: Optional[str],
        disagreement_type: DisagreementType
    ) -> Dict[str, Any]:
        """
        Resolve disagreement and return value, method, and confidence.

        Returns:
            Dict with keys: value, method, confidence
        """
        # Case 1: No disagreement
        if disagreement_type == "NONE":
            if normalized_ml is not None:
                # Both agree, use original ML format (or regex, they should be equivalent)
                return {
                    'value': ml_raw or regex_raw,
                    'method': 'AUTO_NORMALIZED',
                    'confidence': 0.95
                }
            else:
                # Both missing
                return {
                    'value': None,
                    'method': 'AUTO_NORMALIZED',
                    'confidence': 0.0
                }

        # Case 2: Minor formatting difference
        if disagreement_type == "MINOR_FORMATTING":
            # Prefer the source that has a value, or use preference setting
            if normalized_ml is not None and normalized_regex is not None:
                # Both have values but slightly different formatting
                preferred_raw = ml_raw if self.prefer_ml else regex_raw
                return {
                    'value': preferred_raw,
                    'method': 'AUTO_NORMALIZED',
                    'confidence': 0.90
                }
            elif normalized_ml is not None:
                # Only ML has value
                return {
                    'value': ml_raw,
                    'method': 'ML_PREFERRED',
                    'confidence': 0.75
                }
            else:
                # Only regex has value
                return {
                    'value': regex_raw,
                    'method': 'REGEX_PREFERRED',
                    'confidence': 0.80
                }

        # Case 3: Major disagreement
        if disagreement_type == "MAJOR":
            # Use preference setting (default: prefer ML for mileage)
            if self.prefer_ml and normalized_ml is not None:
                return {
                    'value': ml_raw,
                    'method': 'ML_PREFERRED',
                    'confidence': 0.70
                }
            elif not self.prefer_ml and normalized_regex is not None:
                return {
                    'value': regex_raw,
                    'method': 'REGEX_PREFERRED',
                    'confidence': 0.70
                }
            elif normalized_ml is not None:
                return {
                    'value': ml_raw,
                    'method': 'ML_PREFERRED',
                    'confidence': 0.60
                }
            elif normalized_regex is not None:
                return {
                    'value': regex_raw,
                    'method': 'REGEX_PREFERRED',
                    'confidence': 0.70
                }
            else:
                # Both failed (shouldn't happen in MAJOR disagreement, but handle it)
                return {
                    'value': None,
                    'method': 'AUTO_NORMALIZED',
                    'confidence': 0.0
                }

        # Fallback (shouldn't reach here)
        return {
            'value': ml_raw or regex_raw,
            'method': 'AUTO_NORMALIZED',
            'confidence': 0.50
        }


def resolve_mileage(
    ml_raw: Optional[str],
    regex_raw: Optional[str],
    prefer_ml: bool = True,
    manual_override: Optional[str] = None
) -> MileageResolution:
    """
    Convenience function to resolve mileage values.

    Args:
        ml_raw: Raw mileage value from ML extraction
        regex_raw: Raw mileage value from regex extraction
        prefer_ml: If True, prefer ML in case of disagreement (default: True)
        manual_override: Optional manual value (takes precedence)

    Returns:
        MileageResolution object with complete resolution metadata

    Example:
        >>> resolution = resolve_mileage("90000 km", "90000Km")
        >>> resolution.disagreement_type
        'MINOR_FORMATTING'
        >>> resolution.resolved_value
        '90000 km'
        >>> resolution.confidence
        0.90
    """
    resolver = MileageResolver(prefer_ml=prefer_ml)
    return resolver.resolve(ml_raw, regex_raw, manual_override)
