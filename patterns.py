"""
Centralized Regex Patterns
===========================

All regex patterns used across the project in one place.
This ensures consistency and makes updates easier.

Usage:
    from patterns import MILEAGE_PATTERNS, YEAR_PATTERNS, POWER_PATTERNS, FUEL_PATTERNS

    # Simple patterns for filtering/labeling
    for pattern in MILEAGE_PATTERNS:
        match = pattern.search(text)

    # Or use context-aware patterns for production
    from patterns import ContextAwarePatterns
    patterns = ContextAwarePatterns()
    matches = patterns.find_years(text)
"""

import re
from ml.context_aware_patterns import ContextAwarePatterns

# ============================================================================
# MILEAGE PATTERNS
# ============================================================================
# These patterns match mileage values with various formats:
# - "200 000 km", "200km", "200.000 km"
# - "200 tis km", "85 tis. km"
# - "200 xxx km", "200xxx"
# - "200t km", "1.5t km"
# - "200 tisíc km"

MILEAGE_PATTERNS = [
    re.compile(r'\d{1,3}(?:\s?\d{3})*(?:[.,]\d+)?\s?km', re.IGNORECASE),  # "200 000 km", "200km"
    re.compile(r'\d{1,3}(?:\s?\d{3})*(?:\s?tis\.?)\s?km', re.IGNORECASE),  # "200 tis km"
    re.compile(r'\d{1,3}(?:\s?\d{3})*\s?xxx\s?km', re.IGNORECASE),  # "200 xxx km"
    re.compile(r'\d{1,3}(?:[.,]\d+)?\s?t\.?\s?km', re.IGNORECASE),  # "200t km", "1.5t km"
    re.compile(r'\d{1,3}(?:[.,]\d+)?\s?t(?!d|s|i|e|a)', re.IGNORECASE),  # "200t" (not TDI, TSI)
    re.compile(r'\d{1,3}(?:\s?\d{3})*\s?tisíc\s?km', re.IGNORECASE),  # "200 tisíc km"
]

# For compatibility with existing code
MILEAGE_PATTERN_1 = MILEAGE_PATTERNS[0]
MILEAGE_PATTERN_2 = MILEAGE_PATTERNS[1]
MILEAGE_PATTERN_3 = MILEAGE_PATTERNS[2]
MILEAGE_PATTERN_4 = MILEAGE_PATTERNS[3]
MILEAGE_PATTERN_5 = MILEAGE_PATTERNS[4]
MILEAGE_PATTERN_6 = MILEAGE_PATTERNS[5]

# ============================================================================
# YEAR PATTERNS
# ============================================================================
# These patterns match 4-digit years (1900-2029)
# Note: For production use, prefer ContextAwarePatterns which filters out STK dates

YEAR_PATTERNS = [
    re.compile(r'(?:rok\s+výroby|R\.?V\.?|rok|r\.?v\.?|výroba)?\s*(\d{4})\b', re.IGNORECASE),  # With context
    re.compile(r'\b(19\d{2}|20[0-2]\d)\b'),  # Standalone 4-digit year
]

# For compatibility
YEAR_PATTERN = YEAR_PATTERNS[1]  # Most scripts use the standalone pattern

# ============================================================================
# POWER PATTERNS
# ============================================================================
# These patterns match power in kW, PS (horsepower), or koní (Czech for horses)

POWER_PATTERNS = [
    re.compile(r'\d{1,3}\s?kw', re.IGNORECASE),  # "110 kW", "110kW"
    re.compile(r'\d{1,3}\s?ps', re.IGNORECASE),  # "150 PS", "150PS"
    re.compile(r'\d{1,3}\s?koní', re.IGNORECASE),  # "110 koní"
]

# For compatibility
POWER_PATTERN_1 = POWER_PATTERNS[0]
POWER_PATTERN_2 = POWER_PATTERNS[1]
POWER_PATTERN_3 = POWER_PATTERNS[2]
POWER_PATTERN = POWER_PATTERNS[0]  # Most scripts use kW pattern

# ============================================================================
# FUEL PATTERNS
# ============================================================================
# These patterns match fuel types in Czech and English

FUEL_PATTERN = re.compile(
    r'\b(benzin|benzín|nafta|diesel|dýzl|naftak|turbodiesel|tdi|tsi|hybrid|elektro|electric|lpg|cng|plyn)\b',
    re.IGNORECASE
)

FUEL_PATTERNS = [FUEL_PATTERN]  # For consistency with other pattern lists

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def find_mileage(text: str) -> bool:
    """Check if text contains mileage"""
    for pattern in MILEAGE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def find_year(text: str) -> bool:
    """Check if text contains year"""
    for pattern in YEAR_PATTERNS:
        if pattern.search(text):
            return True
    return False


def find_power(text: str) -> bool:
    """Check if text contains power"""
    for pattern in POWER_PATTERNS:
        if pattern.search(text):
            return True
    return False


def find_fuel(text: str) -> bool:
    """Check if text contains fuel type"""
    return FUEL_PATTERN.search(text) is not None


# ============================================================================
# RE-EXPORT CONTEXT-AWARE PATTERNS
# ============================================================================
# For production use with confidence scoring and STK date filtering

__all__ = [
    # Pattern lists
    'MILEAGE_PATTERNS',
    'YEAR_PATTERNS',
    'POWER_PATTERNS',
    'FUEL_PATTERNS',

    # Individual patterns (compatibility)
    'MILEAGE_PATTERN_1',
    'MILEAGE_PATTERN_2',
    'MILEAGE_PATTERN_3',
    'MILEAGE_PATTERN_4',
    'MILEAGE_PATTERN_5',
    'MILEAGE_PATTERN_6',
    'YEAR_PATTERN',
    'POWER_PATTERN',
    'POWER_PATTERN_1',
    'POWER_PATTERN_2',
    'POWER_PATTERN_3',
    'FUEL_PATTERN',

    # Convenience functions
    'find_mileage',
    'find_year',
    'find_power',
    'find_fuel',

    # Context-aware patterns (for production)
    'ContextAwarePatterns',
]
