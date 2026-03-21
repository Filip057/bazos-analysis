"""
Tests for STK/emise date exclusion from year extraction.

STK (technická kontrola) and emissions dates must NOT be extracted as year of manufacture.
Formats: "STK do 2027", "Stk: 02/2027", "STK 02/2027", "emise 03/2027"
"""

import pytest
from ml.context_aware_patterns import ContextAwarePatterns


@pytest.fixture
def patterns():
    return ContextAwarePatterns()


class TestSTKExclusion:
    """STK dates in all formats must be excluded from year matches."""

    @pytest.mark.parametrize("text", [
        "Stk: 02/2027",
        "STK do 02/2027",
        "STK 02/2027",
        "stk platnost 02/2027",
        "STK: 02/2027",
        "stk do 2027",
        "STK do 2027",
        "STK 2027",
        "stk 03/2026",
        "STK platná do 05/2027",
        "stk do: 02/2027",
    ])
    def test_stk_not_extracted_as_year(self, patterns, text):
        matches = patterns.find_years(text)
        years = [m.value for m in matches]
        assert 2027 not in years, f"2027 from STK should not be extracted from: {text}"
        assert 2026 not in years or any(m.confidence == 'low' for m in matches if m.value == 2026), \
            f"STK year should not be extracted as high/medium from: {text}"

    @pytest.mark.parametrize("text", [
        "Emise: 02/2027",
        "emise 03/2027",
        "emisní kontrola 02/2027",
        "emise do 2027",
    ])
    def test_emise_not_extracted_as_year(self, patterns, text):
        matches = patterns.find_years(text)
        years = [m.value for m in matches]
        assert 2027 not in years, f"2027 from emise should not be extracted from: {text}"


class TestSTKWithRealYear:
    """When STK and real production year both present, only production year is extracted."""

    @pytest.mark.parametrize("text,expected_year", [
        ("Rok: 2015, Stk: 02/2027", 2015),
        ("r.v. 2018, STK do 02/2027", 2018),
        ("rok výroby 2012, STK 03/2026, emise 03/2026", 2012),
        ("Škoda Octavia 2016, najeto 150000km, STK 02/2027", 2016),
        ("r.v. 2020 stk do 2027 emise 2027", 2020),
    ])
    def test_real_year_extracted_stk_excluded(self, patterns, text, expected_year):
        matches = patterns.find_years(text)
        years = [m.value for m in matches]
        assert expected_year in years, f"Expected {expected_year} from: {text}, got {years}"
        assert 2027 not in years, f"2027 (STK) should not be in results from: {text}"


class TestRealWorldSTKListings:
    """Real bazos.cz listing patterns with STK."""

    def test_structured_listing_with_stk(self, patterns):
        """Structured listing with Rok: and Stk: fields."""
        text = """Rok: 2015
Objem: 1 499 ccm
Výkon: 77 kw
Převodovka: manuál
Tachometr: 245 000 km
Palivo: nafta
Stk: 02/2027"""
        matches = patterns.find_years(text)
        years = [m.value for m in matches]
        # 2015 should be found (from "Rok: 2015" — not a standard pattern, but from standalone)
        # 2027 should NOT be found
        assert 2027 not in years, f"STK year 2027 should be excluded, got {years}"

    def test_inline_stk_mention(self, patterns):
        """Inline mention: 'STK do 02/2027'."""
        text = "Prodám Mazda CX-5 2.0 118kW, benzín, rok výroby 2012, najeto 132658 km, STK do 02/2027"
        matches = patterns.find_years(text)
        years = [m.value for m in matches]
        assert 2012 in years
        assert 2027 not in years


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
