# Mileage Pattern Support

This document describes all the mileage patterns supported by the Bazos car scraper.

## Overview

The system now supports **47+ different mileage formats** that users commonly write on Bazos.cz, including:
- Standard formats with separators (space, dot, underscore)
- Thousands abbreviations (tis, tisíc, k, t)
- Placeholder formats (xxx, ***)
- With or without "km" suffix
- With or without "najeto" prefix
- Decimal thousands (e.g., "1.5tis km" = 1500 km)

## Supported Formats

### Standard Formats WITH "km"

| Format | Example | Result |
|--------|---------|--------|
| Space separator | `najeto 200 000 km` | 200000 |
| Dot separator | `najeto 200.000 km` | 200000 |
| Underscore separator | `najeto 200_000 km` | 200000 |
| No separator | `najeto 150000 km` | 150000 |
| No space before km | `najeto 150km` | 150000 |
| Comma separator | `najeto 200,000 km` | 200000 |

### Thousands Abbreviations - "tis" / "tisíc" (Czech)

| Format | Example | Result |
|--------|---------|--------|
| tis without km | `najeto 123tis` | 123000 |
| tis with space | `najeto 123 tis` | 123000 |
| tis with dot | `najeto 123tis.` | 123000 |
| tis with space and dot | `najeto 123 tis.` | 123000 |
| tis with km | `najeto 123tis km` | 123000 |
| tis with space and km | `najeto 123 tis km` | 123000 |
| tisíc with km | `najeto 123 tisíc km` | 123000 |
| tisíc without space | `najeto 123tisíc` | 123000 |
| Decimal thousands | `najeto 1.5tis km` | 1500 |

### Thousands Abbreviations - "k"

| Format | Example | Result |
|--------|---------|--------|
| k without space or km | `najeto123k` | 123000 |
| k with space, no km | `najeto 123k` | 123000 |
| k with spaces, no km | `najeto 123 k` | 123000 |
| k with km, no space | `najeto123k km` | 123000 |
| k with km and space | `najeto 123k km` | 123000 |
| k with spaces and km | `najeto 123 k km` | 123000 |

### Thousands Abbreviations - "t"

| Format | Example | Result |
|--------|---------|--------|
| t without space or km | `najeto123t` | 123000 |
| t with space, no km | `najeto 123t` | 123000 |
| t with km, no space | `najeto123t km` | 123000 |
| t with km and space | `najeto 123t km` | 123000 |

**Note:** The system intelligently avoids matching "TDI" and "TSI" (car engine types).

### Placeholder Formats - "xxx"

| Format | Example | Result |
|--------|---------|--------|
| xxx without space or km | `najeto 123xxx` | 123000 |
| xxx with space, no km | `najeto 123 xxx` | 123000 |
| xxx with km, no space | `najeto123xxx km` | 123000 |
| xxx with space and km | `najeto 123xxx km` | 123000 |
| xxx with spaces and km | `najeto 123 xxx km` | 123000 |

### Placeholder Formats - "***"

| Format | Example | Result |
|--------|---------|--------|
| *** without space or km | `najeto 123***` | 123000 |
| *** with space, no km | `najeto 123 ***` | 123000 |
| *** with km, no space | `najeto123*** km` | 123000 |
| *** with space and km | `najeto 123*** km` | 123000 |
| *** with spaces and km | `najeto 123 *** km` | 123000 |

### Formats WITHOUT "najeto" Prefix

The system also matches mileage without explicit context words:

| Format | Example | Result | Confidence |
|--------|---------|--------|------------|
| With tis | `Auto má 150 tis km` | 150000 | medium |
| k suffix | `150k najeto` | 150000 | medium |
| xxx with celkem | `150xxx celkem` | 150000 | medium |
| *** in sentence | `má 150*** km` | 150000 | medium |
| Dot-separated with km | `200.000 km` | 200000 | medium |
| Space-separated, no km | `200 000` | 200000 | medium |

### Formats WITHOUT "km" Suffix

When "najeto" context is present:

| Format | Example | Result | Confidence |
|--------|---------|--------|------------|
| Dot separator | `najeto 123.000` | 123000 | high |
| Space separator | `najeto 123 000` | 123000 | high |
| No separator | `najeto 123000` | 123000 | high |

## Confidence Scoring

The pattern matching system uses three confidence levels:

- **HIGH**: Explicit context like "najeto", "nájezd" + clear mileage format
- **MEDIUM**: Standard format without explicit context, or common abbreviations
- **LOW**: Standalone numbers (rarely used to avoid false positives)

## Smart Features

### 1. Decimal Thousands Support
```
"1.5tis km" → 1500 km
"2.5k" → 2500 km
```

### 2. European Number Format Recognition
The system distinguishes between:
- Decimal point: `1.5` (1.5)
- Thousands separator: `200.000` (200000)

Rule: If there are exactly 3 digits after a dot/comma, it's treated as a thousands separator.

### 3. False Positive Prevention
The system avoids matching:
- Car engine types: TDI, TSI
- Power values: kW, PS
- Other units: km/h, etc.

### 4. Service Records Exclusion
The system excludes mileage from service records:
- `servis při 150000 km` (excluded)
- `rozvody dělány 120000 km` (excluded)
- But captures: `najeto 150000 km` ✓

## File Locations

- **Simple patterns**: `patterns.py` - Basic regex patterns for filtering
- **Context-aware patterns**: `ml/context_aware_patterns.py` - Production patterns with confidence scoring
- **Tests**: `test_mileage_patterns.py` - Comprehensive test suite (47 test cases)

## Usage

### Simple Pattern Matching
```python
from patterns import MILEAGE_PATTERNS

text = "najeto 150tis km"
for pattern in MILEAGE_PATTERNS:
    match = pattern.search(text)
    if match:
        print(f"Found: {match.group()}")
```

### Context-Aware Pattern Matching (Recommended)
```python
from ml.context_aware_patterns import ContextAwarePatterns

patterns = ContextAwarePatterns()
text = "Škoda Octavia 2015, najeto 150tis km, výkon 110 kW"

matches = patterns.find_mileage(text)
for match in matches:
    print(f"Text: '{match.text}'")
    print(f"Value: {match.value} km")
    print(f"Confidence: {match.confidence}")
    print(f"Position: {match.start}-{match.end}")
```

## Testing

Run the comprehensive test suite:
```bash
python test_mileage_patterns.py
```

Expected output: `47 passed, 0 failed`

## Future Enhancements

Potential additions:
- Support for ranges: "100-150 tis km"
- Support for miles: "100k miles" (would need conversion)
- Multi-line formats spanning multiple paragraphs
