"""
Context-Aware Regex Patterns
=============================

Smart regex patterns that use context to avoid false positives.

For YEAR extraction:
- Prioritizes patterns with production year context ("rok výroby", "r.v.")
- Excludes STK dates, service dates, part replacement dates
- Returns matches with confidence scores
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Match:
    """Structured match with confidence"""
    text: str
    value: any  # The actual value (e.g., 2016 for year, 150000 for mileage)
    start: int
    end: int
    confidence: str  # 'high', 'medium', 'low'
    pattern_type: str  # Which pattern matched


class ContextAwarePatterns:
    """Context-aware regex patterns with confidence scoring"""

    # YEAR PATTERNS - Ordered by confidence (high to low)

    # HIGH confidence - explicit production year context
    YEAR_HIGH_CONFIDENCE = [
        re.compile(r'(?:rok\s+výroby|r\.?\s?v\.?|výroba|vyrobeno)\s*[:.]?\s*(\d{4})', re.IGNORECASE),
        re.compile(r'(\d{4})\s*(?:rok\s+výroby|r\.?\s?v\.?)', re.IGNORECASE),
        re.compile(r'rč\.?\s*(\d{4})', re.IGNORECASE),  # "rč. 2016"
    ]

    # MEDIUM confidence - context suggests production year
    YEAR_MEDIUM_CONFIDENCE = [
        re.compile(r'(?:^|\s)(\d{4})\s*(?:km|kw|tdi|tsi)', re.IGNORECASE),  # "2016, 150000 km"
        re.compile(r'(?:škoda|vw|audi|bmw|toyota|ford|mazda)\s+\w+\s+(\d{4})', re.IGNORECASE),  # "Škoda Octavia 2016"
    ]

    # NEGATIVE patterns - EXCLUDE these (STK, service, repairs)
    YEAR_EXCLUDE = [
        re.compile(r'(?:stk|technická|emise|emisní)\s+(?:do|platnost|konec)?\s*(\d{4})', re.IGNORECASE),  # "STK do 2027"
        re.compile(r'(?:servis|serviska|oprava|výměna|vyměněn)\s+(\d{4})', re.IGNORECASE),  # "servis 2023"
        re.compile(r'(?:pneumatiky|pneu|kola|brzdy|motor|převodovka)\s+(?:z|z\s+roku)?\s*(\d{4})', re.IGNORECASE),  # "pneumatiky 2024"
        re.compile(r'nové?\s+(?:od|z)\s+(\d{4})', re.IGNORECASE),  # "nové od 2023"
    ]

    # LOW confidence - standalone year (last resort)
    YEAR_LOW_CONFIDENCE = [
        re.compile(r'\b(19\d{2}|20[0-2]\d)\b'),  # Any 4-digit year
    ]

    # MILEAGE PATTERNS - Context-aware

    MILEAGE_HIGH_CONFIDENCE = [
        re.compile(r'(?:najeto|nájezd|km\s+celkem|počet\s+km)\s*[:.]?\s*(\d{1,3}(?:\s?\d{3})*)\s?km', re.IGNORECASE),
        re.compile(r'(\d{1,3}(?:\s?\d{3})*)\s?km\s+(?:najeto|celkem)', re.IGNORECASE),
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*(\d{1,3})\s?(?:tis|tisíc|t)\.?\s?km', re.IGNORECASE),  # "najeto 150 tis km"
    ]

    MILEAGE_MEDIUM_CONFIDENCE = [
        re.compile(r'\b(\d{1,3}(?:\s?\d{3})*)\s?km\b', re.IGNORECASE),  # Standard "150000 km"
        re.compile(r'\b(\d{1,3})\s?(?:tis|tisíc)\.?\s?km', re.IGNORECASE),  # "150 tis km"
        re.compile(r'\b(\d{1,3})\s?t(?!d|s|i|e)\s?km', re.IGNORECASE),  # "150t km" (not TDI)
        re.compile(r'\b(\d{1,3}(?:\s?\d{3})*)\s?xxx\s?km', re.IGNORECASE),  # "150 xxx km"
    ]

    # EXCLUDE mileage patterns (daily mileage, range, etc.)
    MILEAGE_EXCLUDE = [
        re.compile(r'(?:dojezd|dosah|range)\s+(\d+)\s?km', re.IGNORECASE),  # "dojezd 400 km" (electric car range)
        re.compile(r'(\d+)\s?km\s+(?:denně|měsíčně|ročně)', re.IGNORECASE),  # "50 km denně"
    ]

    # POWER PATTERNS

    POWER_HIGH_CONFIDENCE = [
        re.compile(r'(?:výkon|power|motor)\s*[:.]?\s*(\d{1,3})\s?kw', re.IGNORECASE),
        re.compile(r'(\d{1,3})\s?kw\s+(?:výkon|motor)', re.IGNORECASE),
    ]

    POWER_MEDIUM_CONFIDENCE = [
        re.compile(r'\b(\d{1,3})\s?kw\b', re.IGNORECASE),
        re.compile(r'\b(\d{1,3})\s?ps\b', re.IGNORECASE),
        re.compile(r'\b(\d{1,3})\s?koní\b', re.IGNORECASE),
    ]

    def find_years(self, text: str) -> List[Match]:
        """Find years with confidence scoring"""
        matches = []
        excluded_years = set()

        # First, find years to EXCLUDE
        for pattern in self.YEAR_EXCLUDE:
            for match in pattern.finditer(text):
                year_str = match.group(1)
                excluded_years.add(year_str)

        # HIGH confidence
        for pattern in self.YEAR_HIGH_CONFIDENCE:
            for match in pattern.finditer(text):
                year_str = match.group(1)
                if year_str not in excluded_years and 1990 <= int(year_str) <= 2026:
                    matches.append(Match(
                        text=year_str,
                        value=int(year_str),
                        start=match.start(1),
                        end=match.end(1),
                        confidence='high',
                        pattern_type='production_year_context'
                    ))

        # MEDIUM confidence
        if not matches:  # Only if no high-confidence found
            for pattern in self.YEAR_MEDIUM_CONFIDENCE:
                for match in pattern.finditer(text):
                    year_str = match.group(1)
                    if year_str not in excluded_years and 1990 <= int(year_str) <= 2026:
                        matches.append(Match(
                            text=year_str,
                            value=int(year_str),
                            start=match.start(1),
                            end=match.end(1),
                            confidence='medium',
                            pattern_type='contextual'
                        ))

        # LOW confidence (standalone)
        if not matches:  # Only if nothing else found
            for pattern in self.YEAR_LOW_CONFIDENCE:
                for match in pattern.finditer(text):
                    year_str = match.group(0)
                    if year_str not in excluded_years and 1990 <= int(year_str) <= 2026:
                        matches.append(Match(
                            text=year_str,
                            value=int(year_str),
                            start=match.start(),
                            end=match.end(),
                            confidence='low',
                            pattern_type='standalone'
                        ))

        # Deduplicate and return highest confidence
        return self._deduplicate_matches(matches)

    def find_mileage(self, text: str) -> List[Match]:
        """Find mileage with confidence scoring"""
        matches = []
        excluded_positions = set()

        # Find positions to EXCLUDE
        for pattern in self.MILEAGE_EXCLUDE:
            for match in pattern.finditer(text):
                excluded_positions.add(match.start(1))

        # HIGH confidence
        for pattern in self.MILEAGE_HIGH_CONFIDENCE:
            for match in pattern.finditer(text):
                if match.start(1) not in excluded_positions:
                    value = self._parse_mileage(match.group(1), text[match.start():match.end()])
                    matches.append(Match(
                        text=match.group(0),
                        value=value,
                        start=match.start(),
                        end=match.end(),
                        confidence='high',
                        pattern_type='mileage_context'
                    ))

        # MEDIUM confidence
        if not matches:
            for pattern in self.MILEAGE_MEDIUM_CONFIDENCE:
                for match in pattern.finditer(text):
                    if match.start() not in excluded_positions:
                        value = self._parse_mileage(match.group(1), match.group(0))
                        matches.append(Match(
                            text=match.group(0),
                            value=value,
                            start=match.start(),
                            end=match.end(),
                            confidence='medium',
                            pattern_type='standard'
                        ))

        return self._deduplicate_matches(matches)

    def find_power(self, text: str) -> List[Match]:
        """Find power with confidence scoring"""
        matches = []

        # HIGH confidence
        for pattern in self.POWER_HIGH_CONFIDENCE:
            for match in pattern.finditer(text):
                value = int(re.sub(r'\D', '', match.group(1)))
                if 30 <= value <= 500:  # Reasonable power range
                    matches.append(Match(
                        text=match.group(0),
                        value=value,
                        start=match.start(),
                        end=match.end(),
                        confidence='high',
                        pattern_type='power_context'
                    ))

        # MEDIUM confidence
        if not matches:
            for pattern in self.POWER_MEDIUM_CONFIDENCE:
                for match in pattern.finditer(text):
                    value = int(re.sub(r'\D', '', match.group(1)))
                    if 30 <= value <= 500:
                        matches.append(Match(
                            text=match.group(0),
                            value=value,
                            start=match.start(),
                            end=match.end(),
                            confidence='medium',
                            pattern_type='standard'
                        ))

        return self._deduplicate_matches(matches)

    def _parse_mileage(self, number_str: str, full_text: str) -> int:
        """Parse mileage value, handling abbreviations"""
        # Remove spaces
        number_str = number_str.replace(' ', '').replace('.', '')

        # Check for thousands abbreviations (only immediately after the number)
        # Examples: "150tis km", "150t km", "150 t km"
        # NOT: "najeto 150000 km" (don't match the 't' in 'najeto')
        full_text_lower = full_text.lower()

        # Look for 'tis' or 't' immediately after digits
        if re.search(r'\d+\s*tis\.?\s*km', full_text_lower):
            return int(number_str) * 1000
        elif re.search(r'\d+\s*t\.?\s*km', full_text_lower) and not re.search(r'\d+\s*td[is]', full_text_lower):
            # "150t km" but NOT "150 TDI" (car engine type)
            return int(number_str) * 1000

        return int(number_str)

    def _deduplicate_matches(self, matches: List[Match]) -> List[Match]:
        """Keep only best match at each position"""
        if not matches:
            return []

        # Group by position
        by_position = {}
        for match in matches:
            if match.start not in by_position:
                by_position[match.start] = []
            by_position[match.start].append(match)

        # Keep highest confidence at each position
        confidence_order = {'high': 3, 'medium': 2, 'low': 1}
        result = []

        for position, position_matches in by_position.items():
            best = max(position_matches, key=lambda m: confidence_order[m.confidence])
            result.append(best)

        return sorted(result, key=lambda m: m.start)


# Example usage
if __name__ == "__main__":
    patterns = ContextAwarePatterns()

    # Test with problematic text
    text = "Škoda Octavia 2015, STK do 2027, najeto 150000 km, výkon 110 kW, servis 2023"

    print("Testing context-aware patterns:")
    print(f"Text: {text}\n")

    years = patterns.find_years(text)
    print("YEARS found:")
    for match in years:
        print(f"  '{match.text}' at ({match.start}, {match.end}) - confidence: {match.confidence} - type: {match.pattern_type}")

    mileage = patterns.find_mileage(text)
    print("\nMILEAGE found:")
    for match in mileage:
        print(f"  '{match.text}' = {match.value} km - confidence: {match.confidence}")

    power = patterns.find_power(text)
    print("\nPOWER found:")
    for match in power:
        print(f"  '{match.text}' = {match.value} kW - confidence: {match.confidence}")
