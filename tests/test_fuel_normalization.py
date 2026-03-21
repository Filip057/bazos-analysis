"""
Tests for fuel extraction and normalization.

Covers:
1. normalize_fuel() strict validation — unknown values return None
2. normalize_fuel() composite engine codes (50TDI, 2.0HDi, etc.) → correct fuel type
3. normalize_fuel() rejects non-fuel values (power, mileage, random text)
4. Regex fuel extraction from real listing texts
"""

import pytest
from ml.production_extractor import DataNormalizer


class TestNormalizeFuelStandardValues:
    """Standard fuel values must normalize correctly."""

    @pytest.mark.parametrize("input_val,expected", [
        ("diesel", "diesel"),
        ("nafta", "diesel"),
        ("tdi", "diesel"),
        ("hdi", "diesel"),
        ("cdti", "diesel"),
        ("crdi", "diesel"),
        ("dci", "diesel"),
        ("jtd", "diesel"),
        ("tdci", "diesel"),
        ("benzín", "benzín"),
        ("benzin", "benzín"),
        ("tsi", "benzín"),
        ("lpg", "lpg"),
        ("plyn", "lpg"),
        ("cng", "cng"),
        ("elektro", "elektro"),
        ("electric", "elektro"),
        ("hybrid", "hybrid"),
        ("phev", "hybrid"),
        ("mhev", "hybrid"),
    ])
    def test_standard_values(self, input_val, expected):
        assert DataNormalizer.normalize_fuel(input_val) == expected

    def test_none_input(self):
        assert DataNormalizer.normalize_fuel(None) is None

    def test_empty_string(self):
        assert DataNormalizer.normalize_fuel("") is None


class TestNormalizeFuelCompositeEngineCodes:
    """Engine codes like 50TDI, 2.0HDi must resolve to a fuel type."""

    @pytest.mark.parametrize("input_val,expected", [
        # TDI variants
        ("50TDI", "diesel"),
        ("45TDI", "diesel"),
        ("4.2TDI", "diesel"),
        ("2.0TDI", "diesel"),
        ("3tdi", "diesel"),
        ("2.0BiTDI", "diesel"),
        ("BiTDI", "diesel"),
        # HDi variants
        ("2hdi", "diesel"),
        ("1.6HDi", "diesel"),
        # CDTi variants
        ("1.5CDTi", "diesel"),
        # CRDi variants
        ("1,6CRDi", "diesel"),
        # dCi variants
        ("dti", "diesel"),
        # Other diesel
        ("4.0TDI", "diesel"),
        ("dieslovým", "diesel"),
        ("240xxx.3.0disel", "diesel"),
        ("8/2021,2.0TDI", "diesel"),
        ("2.0tdi,132kw", "diesel"),
        ("d.103kw", None),  # ambiguous 'd' prefix is not enough
        # Benzin composites
        ("TCe", "benzín"),
        ("1.2i", None),  # just 'i' suffix is not fuel
        ("2.0bezín", "benzín"),
        ("GDI/206", "benzín"),
        ("GTI", "benzín"),
    ])
    def test_composite_engine_codes(self, input_val, expected):
        assert DataNormalizer.normalize_fuel(input_val) == expected


class TestNormalizeFuelRejectsNonFuel:
    """Non-fuel values must return None."""

    @pytest.mark.parametrize("input_val", [
        # Power values
        "180kw",
        "173kw",
        "4kw",
        "103kw(140PS",
        "150kw(204hp",
        "89kw(121PS",
        "1910/110kW",
        "2004,120kW",
        # Engine/part codes
        "M54b25",
        "M54B25",
        "8HP45",
        "8K0941006",
        "BCA",
        # Mileage
        "222×××",
        "navigace,121985KM",
        # Random text
        "BOTT",
        "hnije",
        "nehrdzavejucej",
        "nemusel",
        "6st.manuál",
        "Rs4",
        # Year
        "r.v.2012",
        "2003/11",
    ])
    def test_rejects_non_fuel(self, input_val):
        result = DataNormalizer.normalize_fuel(input_val)
        assert result is None, f"Expected None for '{input_val}', got '{result}'"


class TestNormalizeFuelCzechDeclensions:
    """Czech declensions of fuel words must normalize correctly."""

    @pytest.mark.parametrize("input_val,expected", [
        ("dieselový", "diesel"),
        ("dieselovým", "diesel"),
        ("naftový", "diesel"),
        ("naftovým", "diesel"),
        ("naftového", "diesel"),
        ("benzínový", "benzín"),
        ("benzínovým", "benzín"),
        ("hybridní", "hybrid"),
        ("hybridním", "hybrid"),
    ])
    def test_czech_declensions(self, input_val, expected):
        assert DataNormalizer.normalize_fuel(input_val) == expected


class TestRegexFuelExtraction:
    """Test that the regex extractor picks up fuel from real texts."""

    @pytest.fixture
    def extractor(self):
        from ml.production_extractor import ProductionExtractor
        return ProductionExtractor()

    def _extract_fuel_regex(self, text):
        """Extract fuel using only the regex path."""
        from ml.production_extractor import ProductionExtractor
        ext = ProductionExtractor()
        raw = ext._extract_with_regex(text)
        return raw.get('fuel')

    def test_tdi_in_composite_token(self):
        """'2.0TDI' in text should extract 'TDI' as fuel."""
        fuel = self._extract_fuel_regex("VW Golf 2.0TDI 110kW, najeto 150000km")
        assert fuel is not None
        assert 'tdi' in fuel.lower() or 'diesel' in DataNormalizer.normalize_fuel(fuel).lower()

    def test_standalone_diesel(self):
        fuel = self._extract_fuel_regex("Škoda Octavia diesel, rok 2015")
        assert fuel is not None

    def test_benzin_adjective(self):
        fuel = self._extract_fuel_regex("Ford Focus benzínový motor 1.6")
        assert fuel is not None
        assert DataNormalizer.normalize_fuel(fuel) == "benzín"

    def test_lpg_in_text(self):
        fuel = self._extract_fuel_regex("Dacia Sandero 1.2 LPG, rok 2018")
        assert fuel is not None
        assert DataNormalizer.normalize_fuel(fuel) == "lpg"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
