"""
Unit tests for Power Resolution System
"""

import pytest
from ml.power_resolver import (
    PowerResolver,
    PowerNormalizer,
    PowerResolution,
    resolve_power
)


class TestPowerNormalizer:
    """Test power normalization functionality."""

    def test_normalize_kw_variations(self):
        """Test normalization of kW variations."""
        normalizer = PowerNormalizer()

        assert normalizer.normalize("151 kw") == "151kw"
        assert normalizer.normalize("151kw") == "151kw"
        assert normalizer.normalize("151 KW") == "151kw"
        assert normalizer.normalize("151KW") == "151kw"
        assert normalizer.normalize("151  kw") == "151kw"

    def test_normalize_ps_variations(self):
        """Test normalization of PS/HP variations."""
        normalizer = PowerNormalizer()

        assert normalizer.normalize("110 PS") == "110ps"
        assert normalizer.normalize("110 ps") == "110ps"
        assert normalizer.normalize("110PS") == "110ps"
        assert normalizer.normalize("110 hp") == "110ps"
        assert normalizer.normalize("110 HP") == "110ps"

    def test_normalize_czech_variations(self):
        """Test normalization of Czech power units."""
        normalizer = PowerNormalizer()

        assert normalizer.normalize("110 koní") == "110ps"
        assert normalizer.normalize("110 koně") == "110ps"
        assert normalizer.normalize("110 kon") == "110ps"

    def test_normalize_edge_cases(self):
        """Test edge cases in normalization."""
        normalizer = PowerNormalizer()

        # None and empty
        assert normalizer.normalize(None) is None
        assert normalizer.normalize("") is None
        assert normalizer.normalize("   ") is None

        # Invalid format
        assert normalizer.normalize("kw 151") is None
        assert normalizer.normalize("power") is None
        assert normalizer.normalize("151") is None  # No unit

        # Unknown unit
        assert normalizer.normalize("151 watts") is None

    def test_extract_numeric(self):
        """Test numeric extraction from power strings."""
        normalizer = PowerNormalizer()

        assert normalizer.extract_numeric("151 kw") == 151
        assert normalizer.extract_numeric("151kw") == 151
        assert normalizer.extract_numeric("110 PS") == 110
        assert normalizer.extract_numeric("99 koní") == 99

        # Edge cases
        assert normalizer.extract_numeric(None) is None
        assert normalizer.extract_numeric("") is None
        assert normalizer.extract_numeric("no numbers") is None


class TestPowerResolverDisagreementClassification:
    """Test disagreement classification logic."""

    def test_no_disagreement_both_same(self):
        """Test when both extractions agree."""
        resolver = PowerResolver()

        ml_raw = "151 kw"
        regex_raw = "151kw"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "NONE"

    def test_no_disagreement_both_none(self):
        """Test when both extractions are missing."""
        resolver = PowerResolver()

        disagreement = resolver._classify_disagreement(None, None)
        assert disagreement == "NONE"

    def test_minor_formatting_same_number_different_units(self):
        """Test minor disagreement with same number, different units."""
        resolver = PowerResolver()

        ml_raw = "110 kw"
        regex_raw = "110 ps"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "MINOR_FORMATTING"

    def test_minor_formatting_one_missing(self):
        """Test when one extraction is missing."""
        resolver = PowerResolver()

        ml_normalized = "151kw"
        regex_normalized = None

        disagreement = resolver._classify_disagreement(ml_normalized, regex_normalized)
        assert disagreement == "MINOR_FORMATTING"

    def test_major_disagreement_different_numbers(self):
        """Test major disagreement with different numbers."""
        resolver = PowerResolver()

        ml_raw = "151 kw"
        regex_raw = "110 kw"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "MAJOR"


class TestPowerResolverResolution:
    """Test power resolution logic."""

    def test_perfect_agreement(self):
        """Test resolution when ML and regex perfectly agree."""
        resolver = PowerResolver()

        resolution = resolver.resolve("151 kw", "151kw")

        assert resolution.ml_raw == "151 kw"
        assert resolution.regex_raw == "151kw"
        assert resolution.normalized_ml == "151kw"
        assert resolution.normalized_regex == "151kw"
        assert resolution.disagreement_type == "NONE"
        assert resolution.resolved_value == "151 kw"  # Uses ML format
        assert resolution.resolution_method == "AUTO_NORMALIZED"
        assert resolution.confidence == 0.95

    def test_minor_formatting_difference(self):
        """Test resolution with minor formatting difference."""
        resolver = PowerResolver(prefer_ml=False)

        resolution = resolver.resolve("151 KW", "151 kw")

        assert resolution.disagreement_type == "NONE"  # Normalized to same
        assert resolution.resolution_method == "AUTO_NORMALIZED"
        assert resolution.confidence == 0.95

    def test_only_ml_present(self):
        """Test resolution when only ML has a value."""
        resolver = PowerResolver()

        resolution = resolver.resolve("151 kw", None)

        assert resolution.ml_raw == "151 kw"
        assert resolution.regex_raw is None
        assert resolution.normalized_ml == "151kw"
        assert resolution.normalized_regex is None
        assert resolution.disagreement_type == "MINOR_FORMATTING"
        assert resolution.resolved_value == "151 kw"
        assert resolution.resolution_method == "ML_PREFERRED"
        assert resolution.confidence == 0.75

    def test_only_regex_present(self):
        """Test resolution when only regex has a value."""
        resolver = PowerResolver()

        resolution = resolver.resolve(None, "151 kw")

        assert resolution.ml_raw is None
        assert resolution.regex_raw == "151 kw"
        assert resolution.normalized_ml is None
        assert resolution.normalized_regex == "151kw"
        assert resolution.disagreement_type == "MINOR_FORMATTING"
        assert resolution.resolved_value == "151 kw"
        assert resolution.resolution_method == "REGEX_PREFERRED"
        assert resolution.confidence == 0.80

    def test_major_disagreement_prefer_regex(self):
        """Test major disagreement with regex preference."""
        resolver = PowerResolver(prefer_ml=False)

        resolution = resolver.resolve("151 kw", "110 kw")

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "110 kw"
        assert resolution.resolution_method == "REGEX_PREFERRED"
        assert resolution.confidence == 0.70

    def test_major_disagreement_prefer_ml(self):
        """Test major disagreement with ML preference."""
        resolver = PowerResolver(prefer_ml=True)

        resolution = resolver.resolve("151 kw", "110 kw")

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "151 kw"
        assert resolution.resolution_method == "ML_PREFERRED"
        assert resolution.confidence == 0.60

    def test_manual_override(self):
        """Test manual override takes precedence."""
        resolver = PowerResolver()

        resolution = resolver.resolve(
            ml_raw="151 kw",
            regex_raw="110 kw",
            manual_override="145 kw"
        )

        assert resolution.disagreement_type == "NONE"  # Manual bypasses disagreement
        assert resolution.resolved_value == "145 kw"
        assert resolution.resolution_method == "MANUAL"
        assert resolution.confidence == 1.0

    def test_both_missing(self):
        """Test when both extractions are missing."""
        resolver = PowerResolver()

        resolution = resolver.resolve(None, None)

        assert resolution.ml_raw is None
        assert resolution.regex_raw is None
        assert resolution.normalized_ml is None
        assert resolution.normalized_regex is None
        assert resolution.disagreement_type == "NONE"
        assert resolution.resolved_value is None
        assert resolution.resolution_method == "AUTO_NORMALIZED"
        assert resolution.confidence == 0.0


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_resolve_power_function(self):
        """Test the convenience function works correctly."""
        resolution = resolve_power("151 kw", "151kw")

        assert resolution.disagreement_type == "NONE"
        assert resolution.resolved_value == "151 kw"
        assert resolution.confidence == 0.95

    def test_resolve_power_with_preference(self):
        """Test preference parameter."""
        resolution = resolve_power("151 kw", "110 kw", prefer_ml=True)

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "151 kw"
        assert resolution.resolution_method == "ML_PREFERRED"

    def test_resolve_power_with_manual(self):
        """Test manual override parameter."""
        resolution = resolve_power(
            "151 kw",
            "110 kw",
            manual_override="145 kw"
        )

        assert resolution.resolved_value == "145 kw"
        assert resolution.resolution_method == "MANUAL"


class TestResolutionToDict:
    """Test serialization of resolution results."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        resolution = resolve_power("151 kw", "151kw")
        result_dict = resolution.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict['ml_raw'] == "151 kw"
        assert result_dict['regex_raw'] == "151kw"
        assert result_dict['normalized_ml'] == "151kw"
        assert result_dict['normalized_regex'] == "151kw"
        assert result_dict['disagreement_type'] == "NONE"
        assert result_dict['resolved_value'] == "151 kw"
        assert result_dict['resolution_method'] == "AUTO_NORMALIZED"
        assert result_dict['confidence'] == 0.95


class TestRealWorldScenarios:
    """Test real-world scenarios from car listings."""

    def test_typical_agreement_scenario(self):
        """Test typical case where both methods agree."""
        # ML might extract "110 KW", regex might extract "110 kW"
        resolution = resolve_power("110 KW", "110 kW")

        assert resolution.disagreement_type == "NONE"
        assert resolution.confidence == 0.95

    def test_ml_finds_regex_misses(self):
        """Test when ML finds power but regex doesn't."""
        resolution = resolve_power("145 kw", None)

        assert resolution.resolved_value == "145 kw"
        assert resolution.resolution_method == "ML_PREFERRED"
        assert resolution.confidence == 0.75

    def test_regex_finds_ml_misses(self):
        """Test when regex finds power but ML doesn't."""
        resolution = resolve_power(None, "145 kw")

        assert resolution.resolved_value == "145 kw"
        assert resolution.resolution_method == "REGEX_PREFERRED"
        assert resolution.confidence == 0.80

    def test_conflicting_extractions(self):
        """Test when ML and regex extract different values."""
        # Could happen if text has multiple power mentions
        resolution = resolve_power("110 kw", "150 kw", prefer_ml=False)

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "150 kw"  # Regex preferred
        assert resolution.confidence == 0.70

    def test_unit_conversion_scenario(self):
        """Test when different units are extracted."""
        # 110 kW ≈ 150 PS, but we don't do conversion
        resolution = resolve_power("110 kw", "150 ps")

        # Different units with different numbers -> MAJOR
        assert resolution.disagreement_type == "MAJOR"

    def test_none_found_scenario(self):
        """Test when neither method finds power."""
        resolution = resolve_power(None, None)

        assert resolution.resolved_value is None
        assert resolution.confidence == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
