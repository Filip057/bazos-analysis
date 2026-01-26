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
        # NEW: Exclude service/repair dates (rozvody 2024, brzdy 2025, etc.)
        re.compile(r'(?:rozvody|rozvodový|řemen|řemeny|brzdy|brzdové|destičky|kotouče|olej|filtr|filtry)\s+(?:dělané?|dělaný|vyměněné?|vyměněn[yoa]?|při|z|ze)\s*(\d{4})', re.IGNORECASE),
        re.compile(r'(?:dělané?|vyměněné?|vyměněn[yoa]?|oprava|opraveno)\s+(?:při|v|ve|z)?\s*(\d{4})', re.IGNORECASE),  # "dělány 2023", "vyměněny 2023"
    ]

    # LOW confidence - standalone year (last resort)
    YEAR_LOW_CONFIDENCE = [
        re.compile(r'\b(19\d{2}|20[0-2]\d)\b'),  # Any 4-digit year
    ]

    # MILEAGE PATTERNS - Context-aware (EXPANDED: support all user variations)

    MILEAGE_HIGH_CONFIDENCE = [
        # With explicit context (najeto, nájezd, etc.) + km
        re.compile(r'(?:najeto|nájezd|km\s+celkem|počet\s+km)\s*[:.]?\s*((\d{1,3}(?:[\s._]?\d{3})+)\s?km)', re.IGNORECASE),  # "najeto 200 000 km"
        re.compile(r'((\d{1,3}(?:[\s._]?\d{3})+)\s?km)\s+(?:najeto|celkem)', re.IGNORECASE),  # "200 000 km najeto"

        # With explicit context + separator BUT NO km (needs explicit "najeto" context)
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{1,3}[\s._]\d{3}(?:[\s._]\d{3})?)(?!\s?km))', re.IGNORECASE),  # "najeto 123 000", "najeto 123.000"

        # With thousands abbreviations + context
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{1,3}(?:[.,]\d+)?)\s?(?:tis|tisíc)\.?\s?(?:km)?)', re.IGNORECASE),  # "najeto 150 tis", "najeto 150tis km"
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{1,3}(?:[.,]\d+)?)\s?k(?:\s?km)?)', re.IGNORECASE),  # "najeto 150k", "najeto150k km"
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{1,3}(?:[.,]\d+)?)\s?t\.?(?:\s?km)?)', re.IGNORECASE),  # "najeto 150t", "najeto 150t km"

        # With placeholder formats + context
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{1,3})\s?xxx(?:\s?km)?)', re.IGNORECASE),  # "najeto 150xxx", "najeto150xxx km"
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{1,3})\s?\*{3}(?:\s?km)?)', re.IGNORECASE),  # "najeto 150***", "najeto150*** km"

        # Standard format + context (no thousands separator)
        re.compile(r'(?:najeto|nájezd)\s*[:.]?\s*((\d{5,6})(?:\s?km)?)', re.IGNORECASE),  # "najeto 150000", "najeto150000 km"
    ]

    MILEAGE_MEDIUM_CONFIDENCE = [
        # Standard formats WITH km
        re.compile(r'\b((\d{1,3}(?:[\s._]\d{3})+)\s?km)\b', re.IGNORECASE),  # "150 000 km", "150.000 km", "150_000km"
        re.compile(r'\b((\d{5,6})\s?km)\b', re.IGNORECASE),  # "150000 km", "150000km"

        # Thousands abbreviations WITH km
        re.compile(r'\b((\d{1,3}(?:[.,]\d+)?)\s?(?:tis|tisíc)\.?\s?km)', re.IGNORECASE),  # "150 tis km", "150tis. km"
        re.compile(r'\b((\d{1,3}(?:[.,]\d+)?)\s?k\s?km)', re.IGNORECASE),  # "150k km", "150 k km"
        re.compile(r'\b((\d{1,3}(?:[.,]\d+)?)\s?t(?!d|s|i|e)\s?km)', re.IGNORECASE),  # "150t km" (not TDI)

        # Placeholder formats WITH km
        re.compile(r'\b((\d{1,3})\s?xxx\s?km)', re.IGNORECASE),  # "150 xxx km", "150xxx km"
        re.compile(r'\b((\d{1,3})\s?\*{3}\s?km)', re.IGNORECASE),  # "150 *** km", "150*** km"

        # Thousands abbreviations WITHOUT km (standalone)
        re.compile(r'\b((\d{1,3}(?:[.,]\d+)?)\s?(?:tis|tisíc)\.?)(?!\w)', re.IGNORECASE),  # "150tis", "150 tis."
        re.compile(r'\b((\d{1,3}(?:[.,]\d+)?)k)(?!w|m|\w)', re.IGNORECASE),  # "150k" (not kW, km)
        re.compile(r'\b((\d{1,3}(?:[.,]\d+)?)\s?t)(?!d|s|i|e|a|\w)', re.IGNORECASE),  # "150t" (not TDI, TSI)

        # Placeholder formats WITHOUT km
        re.compile(r'\b((\d{1,3})\s?xxx)(?!\w)', re.IGNORECASE),  # "150xxx", "150 xxx"
        re.compile(r'\b((\d{1,3})\s?\*{3})(?!\w)', re.IGNORECASE),  # "150***", "150 ***"

        # Standard formats WITHOUT km (with separator) - must have 5+ total digits to be mileage
        re.compile(r'\b((\d{1,3}[\s._]\d{3}(?:[\s._]\d{3})?))(?!\s?k[mw]|\w)', re.IGNORECASE),  # "150 000", "150.000" (not followed by km/kw)
        re.compile(r'\b((\d{5,6}))(?!\s?k[mw]|\d)', re.IGNORECASE),  # "150000" (5-6 digits)
    ]

    # EXCLUDE mileage patterns (daily mileage, range, service records, etc.)
    MILEAGE_EXCLUDE = [
        re.compile(r'(?:dojezd|dosah|range)\s+(\d+)\s?km', re.IGNORECASE),  # "dojezd 400 km" (electric car range)
        re.compile(r'(\d+)\s?km\s+(?:denně|měsíčně|ročně)', re.IGNORECASE),  # "50 km denně"
        # NEW: Exclude service-related mileage (servis při xxx km, rozvody při xxx km)
        re.compile(r'(?:servis|serviska|poslední\s+servis|oprava|výměna|vyměněn|dělané?)\s+(?:při|v|ve|na)?\s*[:.]?\s*(\d{1,3}(?:[\s.]?\d{3})*)\s?km', re.IGNORECASE),
        re.compile(r'(?:rozvody|rozvodový|řemen|brzdy|olej|filtr|filtry)\s+(?:při|dělané?|vyměněné?)\s+(\d{1,3}(?:[\s.]?\d{3})*)\s?km', re.IGNORECASE),
    ]

    # POWER PATTERNS - ONLY kW (FIXED: exclude HP/PS/koně)

    POWER_HIGH_CONFIDENCE = [
        re.compile(r'(?:výkon|power|motor)\s*[:.]?\s*((\d{1,3})\s?kw)', re.IGNORECASE),
        re.compile(r'((\d{1,3})\s?kw)\s+(?:výkon|motor)', re.IGNORECASE),
    ]

    POWER_MEDIUM_CONFIDENCE = [
        re.compile(r'\b((\d{1,3})\s?kw)\b', re.IGNORECASE),  # Only kW!
    ]

    # EXCLUDE power in HP/PS/koně (different unit, would need conversion)
    POWER_EXCLUDE = [
        re.compile(r'\b(\d{1,3})\s?(?:hp|ps|koní|koně|kon)\b', re.IGNORECASE),  # HP/PS/koně
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
                    value = self._parse_mileage(match.group(2), match.group(1))
                    matches.append(Match(
                        text=match.group(1),  # Capture just "160.373 km", not "najeto: 160.373 km"
                        value=value,
                        start=match.start(1),
                        end=match.end(1),
                        confidence='high',
                        pattern_type='mileage_context'
                    ))

        # MEDIUM confidence
        if not matches:
            for pattern in self.MILEAGE_MEDIUM_CONFIDENCE:
                for match in pattern.finditer(text):
                    if match.start(1) not in excluded_positions:
                        value = self._parse_mileage(match.group(2), match.group(1))
                        matches.append(Match(
                            text=match.group(1),  # Just "160.373 km"
                            value=value,
                            start=match.start(1),
                            end=match.end(1),
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
                value = int(re.sub(r'\D', '', match.group(2)))
                if 30 <= value <= 500:  # Reasonable power range
                    matches.append(Match(
                        text=match.group(1),  # Just "88 kw", not "Výkon 88 kw"
                        value=value,
                        start=match.start(1),
                        end=match.end(1),
                        confidence='high',
                        pattern_type='power_context'
                    ))

        # MEDIUM confidence
        if not matches:
            for pattern in self.POWER_MEDIUM_CONFIDENCE:
                for match in pattern.finditer(text):
                    value = int(re.sub(r'\D', '', match.group(2)))
                    if 30 <= value <= 500:
                        matches.append(Match(
                            text=match.group(1),  # Just "88 kw"
                            value=value,
                            start=match.start(1),
                            end=match.end(1),
                            confidence='medium',
                            pattern_type='standard'
                        ))

        return self._deduplicate_matches(matches)

    def _parse_mileage(self, number_str: str, full_text: str) -> int:
        """Parse mileage value, handling abbreviations

        Handles formats:
        - 150 000, 150.000, 150_000 → 150000
        - 150tis, 150k, 150t → 150000 (multiply by 1000)
        - 150xxx, 150*** → 150000 (multiply by 1000)
        - 150000 → 150000 (already full number)
        - 1.5tis → 1500 (decimal thousands)
        """
        full_text_lower = full_text.lower().strip()

        # Check for thousands indicators FIRST (before parsing the number)
        # This prevents false matches like "200 000 km" matching "0 k"
        has_tis = bool(re.search(r'^(\d+(?:[.,]\d+)?)\s*tis(?:íc)?\.?(?:\s*km)?$', full_text_lower))
        has_k = bool(re.search(r'^(\d+(?:[.,]\d+)?)\s*k\s*(?:km)?$', full_text_lower))
        has_t = bool(re.search(r'^(\d+(?:[.,]\d+)?)\s*t\.?\s*(?:km)?$', full_text_lower) and 'tdi' not in full_text_lower and 'tsi' not in full_text_lower)
        has_xxx = bool(re.search(r'^(\d+)\s*xxx\s*(?:km)?$', full_text_lower))
        has_stars = '***' in full_text or '* * *' in full_text

        # Determine if we should multiply by 1000
        multiply_by_thousand = has_tis or has_k or has_t or has_xxx or has_stars

        # Parse the numeric value
        # Distinguish between decimal point (1.5) and thousands separator (200.000)
        # European format: dot with exactly 3 digits = thousands separator
        # Otherwise: decimal point

        # Check for thousands separator (e.g., "200.000" or "200,000")
        thousands_sep_match = re.match(r'(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?', number_str)
        if thousands_sep_match and not multiply_by_thousand:
            # It's a thousands separator format like "200.000" or "200,000"
            # Join all the groups
            parts = [thousands_sep_match.group(1), thousands_sep_match.group(2)]
            if thousands_sep_match.group(3):
                parts.append(thousands_sep_match.group(3))
            base_value = int(''.join(parts))
            return base_value

        # Check for decimal number with thousands indicator (e.g., "1.5tis")
        decimal_match = re.match(r'(\d+)[.,](\d{1,2})', number_str)
        if decimal_match and multiply_by_thousand:
            # It's a decimal like "1.5tis" → 1.5 * 1000 = 1500
            value_str = f"{decimal_match.group(1)}.{decimal_match.group(2)}"
            base_value = float(value_str)
            return int(base_value * 1000)

        # Remove separators for integer parsing
        cleaned = number_str.replace(' ', '').replace('.', '').replace('_', '').replace(',', '').replace('\n', '').replace('\t', '').replace('\r', '')

        # Extract only the numeric part
        numbers = re.findall(r'\d+', cleaned)
        if not numbers:
            return 0

        # Join all numbers (handles cases like "200 000" → "200000")
        joined_number = ''.join(numbers)
        base_value = int(joined_number)

        # If we have a thousands indicator, multiply
        if multiply_by_thousand and base_value < 1000:
            return base_value * 1000

        return base_value

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
