"""
Unit tests for Mileage Resolution System
"""

import pytest
from ml.mileage_resolver import (
    MileageResolver,
    MileageNormalizer,
    MileageResolution,
    resolve_mileage
)


class TestMileageNormalizer:
    """Test mileage normalization functionality."""

    def test_normalize_km_variations(self):
        """Test normalization of km variations."""
        normalizer = MileageNormalizer()

        assert normalizer.normalize("90000 km") == "90000km"
        assert normalizer.normalize("90000km") == "90000km"
        assert normalizer.normalize("90000 Km") == "90000km"
        assert normalizer.normalize("90000Km") == "90000km"
        assert normalizer.normalize("90000 KM") == "90000km"
        assert normalizer.normalize("90000KM") == "90000km"

    def test_normalize_with_spaces_in_numbers(self):
        """Test normalization with spaces in numbers."""
        normalizer = MileageNormalizer()

        assert normalizer.normalize("90 000 km") == "90000km"
        assert normalizer.normalize("150 000 km") == "150000km"
        assert normalizer.normalize("1 500 km") == "1500km"

    def test_normalize_miles(self):
        """Test normalization of miles."""
        normalizer = MileageNormalizer()

        assert normalizer.normalize("50000 mi") == "50000mi"
        assert normalizer.normalize("50000 miles") == "50000mi"
        assert normalizer.normalize("50000 mile") == "50000mi"

    def test_normalize_edge_cases(self):
        """Test edge cases in normalization."""
        normalizer = MileageNormalizer()

        # None and empty
        assert normalizer.normalize(None) is None
        assert normalizer.normalize("") is None
        assert normalizer.normalize("   ") is None

        # Invalid format
        assert normalizer.normalize("km 90000") is None
        assert normalizer.normalize("mileage") is None
        assert normalizer.normalize("90000") is None  # No unit

        # Unknown unit
        assert normalizer.normalize("90000 meters") is None

    def test_extract_numeric(self):
        """Test numeric extraction from mileage strings."""
        normalizer = MileageNormalizer()

        assert normalizer.extract_numeric("90000 km") == 90000
        assert normalizer.extract_numeric("90000km") == 90000
        assert normalizer.extract_numeric("150 000 km") == 150000
        assert normalizer.extract_numeric("50000 mi") == 50000

        # Edge cases
        assert normalizer.extract_numeric(None) is None
        assert normalizer.extract_numeric("") is None
        assert normalizer.extract_numeric("no numbers") is None


class TestMileageResolverDisagreementClassification:
    """Test disagreement classification logic."""

    def test_no_disagreement_both_same(self):
        """Test when both extractions agree."""
        resolver = MileageResolver()

        ml_raw = "90000 km"
        regex_raw = "90000km"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "NONE"

    def test_no_disagreement_both_none(self):
        """Test when both extractions are missing."""
        resolver = MileageResolver()

        disagreement = resolver._classify_disagreement(None, None)
        assert disagreement == "NONE"

    def test_minor_formatting_case_difference(self):
        """Test minor disagreement with case difference."""
        resolver = MileageResolver()

        ml_raw = "90000 km"
        regex_raw = "90000 Km"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "NONE"  # After normalization, they're the same

    def test_minor_formatting_spacing_difference(self):
        """Test minor disagreement with spacing difference."""
        resolver = MileageResolver()

        ml_raw = "90 000 km"
        regex_raw = "90000km"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "NONE"  # After normalization, they're the same

    def test_minor_formatting_one_missing(self):
        """Test when one extraction is missing."""
        resolver = MileageResolver()

        ml_normalized = "90000km"
        regex_normalized = None

        disagreement = resolver._classify_disagreement(ml_normalized, regex_normalized)
        assert disagreement == "MINOR_FORMATTING"

    def test_major_disagreement_different_numbers(self):
        """Test major disagreement with different numbers."""
        resolver = MileageResolver()

        ml_raw = "90000 km"
        regex_raw = "150000 km"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "MAJOR"

    def test_minor_formatting_same_number_different_units(self):
        """Test minor disagreement with same number, different units."""
        resolver = MileageResolver()

        ml_raw = "90000 km"
        regex_raw = "90000 mi"

        normalized_ml = resolver.normalizer.normalize(ml_raw)
        normalized_regex = resolver.normalizer.normalize(regex_raw)

        disagreement = resolver._classify_disagreement(normalized_ml, normalized_regex)
        assert disagreement == "MINOR_FORMATTING"


class TestMileageResolverResolution:
    """Test mileage resolution logic."""

    def test_perfect_agreement(self):
        """Test resolution when ML and regex perfectly agree."""
        resolver = MileageResolver()

        resolution = resolver.resolve("90000 km", "90000km")

        assert resolution.ml_raw == "90000 km"
        assert resolution.regex_raw == "90000km"
        assert resolution.normalized_ml == "90000km"
        assert resolution.normalized_regex == "90000km"
        assert resolution.disagreement_type == "NONE"
        assert resolution.resolved_value == "90000 km"  # Uses ML format
        assert resolution.resolution_method == "AUTO_NORMALIZED"
        assert resolution.confidence == 0.95

    def test_minor_formatting_difference_prefer_ml(self):
        """Test resolution with minor formatting difference, preferring ML."""
        resolver = MileageResolver(prefer_ml=True)

        resolution = resolver.resolve("90000 km", "90000Km")

        assert resolution.disagreement_type == "NONE"  # Normalized to same
        assert resolution.resolved_value == "90000 km"  # Uses ML format
        assert resolution.resolution_method == "AUTO_NORMALIZED"
        assert resolution.confidence == 0.95

    def test_only_ml_present(self):
        """Test resolution when only ML has a value."""
        resolver = MileageResolver()

        resolution = resolver.resolve("90000 km", None)

        assert resolution.ml_raw == "90000 km"
        assert resolution.regex_raw is None
        assert resolution.normalized_ml == "90000km"
        assert resolution.normalized_regex is None
        assert resolution.disagreement_type == "MINOR_FORMATTING"
        assert resolution.resolved_value == "90000 km"
        assert resolution.resolution_method == "ML_PREFERRED"
        assert resolution.confidence == 0.75

    def test_only_regex_present(self):
        """Test resolution when only regex has a value."""
        resolver = MileageResolver()

        resolution = resolver.resolve(None, "90000 km")

        assert resolution.ml_raw is None
        assert resolution.regex_raw == "90000 km"
        assert resolution.normalized_ml is None
        assert resolution.normalized_regex == "90000km"
        assert resolution.disagreement_type == "MINOR_FORMATTING"
        assert resolution.resolved_value == "90000 km"
        assert resolution.resolution_method == "REGEX_PREFERRED"
        assert resolution.confidence == 0.80

    def test_major_disagreement_prefer_ml(self):
        """Test major disagreement with ML preference (default for mileage)."""
        resolver = MileageResolver(prefer_ml=True)

        resolution = resolver.resolve("90000 km", "150000 km")

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "90000 km"
        assert resolution.resolution_method == "ML_PREFERRED"
        assert resolution.confidence == 0.70

    def test_major_disagreement_prefer_regex(self):
        """Test major disagreement with regex preference."""
        resolver = MileageResolver(prefer_ml=False)

        resolution = resolver.resolve("90000 km", "150000 km")

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "150000 km"
        assert resolution.resolution_method == "REGEX_PREFERRED"
        assert resolution.confidence == 0.70

    def test_manual_override(self):
        """Test manual override takes precedence."""
        resolver = MileageResolver()

        resolution = resolver.resolve(
            ml_raw="90000 km",
            regex_raw="150000 km",
            manual_override="120000 km"
        )

        assert resolution.disagreement_type == "NONE"  # Manual bypasses disagreement
        assert resolution.resolved_value == "120000 km"
        assert resolution.resolution_method == "MANUAL"
        assert resolution.confidence == 1.0

    def test_both_missing(self):
        """Test when both extractions are missing."""
        resolver = MileageResolver()

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

    def test_resolve_mileage_function(self):
        """Test the convenience function works correctly."""
        resolution = resolve_mileage("90000 km", "90000km")

        assert resolution.disagreement_type == "NONE"
        assert resolution.resolved_value == "90000 km"
        assert resolution.confidence == 0.95

    def test_resolve_mileage_with_preference(self):
        """Test preference parameter."""
        resolution = resolve_mileage("90000 km", "150000 km", prefer_ml=True)

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "90000 km"
        assert resolution.resolution_method == "ML_PREFERRED"

    def test_resolve_mileage_with_manual(self):
        """Test manual override parameter."""
        resolution = resolve_mileage(
            "90000 km",
            "150000 km",
            manual_override="120000 km"
        )

        assert resolution.resolved_value == "120000 km"
        assert resolution.resolution_method == "MANUAL"


class TestResolutionToDict:
    """Test serialization of resolution results."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        resolution = resolve_mileage("90000 km", "90000km")
        result_dict = resolution.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict['ml_raw'] == "90000 km"
        assert result_dict['regex_raw'] == "90000km"
        assert result_dict['normalized_ml'] == "90000km"
        assert result_dict['normalized_regex'] == "90000km"
        assert result_dict['disagreement_type'] == "NONE"
        assert result_dict['resolved_value'] == "90000 km"
        assert result_dict['resolution_method'] == "AUTO_NORMALIZED"
        assert result_dict['confidence'] == 0.95


class TestRealWorldScenarios:
    """Test real-world scenarios from car listings."""

    def test_typical_agreement_scenario(self):
        """Test typical case where both methods agree."""
        # ML might extract "90000 km", regex might extract "90000 Km"
        resolution = resolve_mileage("90000 km", "90000 Km")

        assert resolution.disagreement_type == "NONE"
        assert resolution.confidence == 0.95

    def test_ml_finds_regex_misses(self):
        """Test when ML finds mileage but regex doesn't."""
        resolution = resolve_mileage("90000 km", None)

        assert resolution.resolved_value == "90000 km"
        assert resolution.resolution_method == "ML_PREFERRED"
        assert resolution.confidence == 0.75

    def test_regex_finds_ml_misses(self):
        """Test when regex finds mileage but ML doesn't."""
        resolution = resolve_mileage(None, "90000 km")

        assert resolution.resolved_value == "90000 km"
        assert resolution.resolution_method == "REGEX_PREFERRED"
        assert resolution.confidence == 0.80

    def test_conflicting_extractions(self):
        """Test when ML and regex extract different values."""
        # Could happen if text has multiple mileage mentions
        resolution = resolve_mileage("90000 km", "150000 km", prefer_ml=True)

        assert resolution.disagreement_type == "MAJOR"
        assert resolution.resolved_value == "90000 km"  # ML preferred
        assert resolution.confidence == 0.70

    def test_spacing_difference_scenario(self):
        """Test when spacing differs between extractions."""
        # ML extracts with space in number, regex without
        resolution = resolve_mileage("90 000 km", "90000 km")

        # After normalization, these should be the same
        assert resolution.disagreement_type == "NONE"
        assert resolution.confidence == 0.95

    def test_case_difference_scenario(self):
        """Test when case differs between extractions (the user's example)."""
        # ML: "90000 km", Regex: "90000Km"
        resolution = resolve_mileage("90000 km", "90000Km", prefer_ml=True)

        # After normalization, these are the same
        assert resolution.disagreement_type == "NONE"
        assert resolution.resolved_value == "90000 km"  # Keep ML format
        assert resolution.confidence == 0.95

    def test_none_found_scenario(self):
        """Test when neither method finds mileage."""
        resolution = resolve_mileage(None, None)

        assert resolution.resolved_value is None
        assert resolution.confidence == 0.0

    def test_unit_difference_scenario(self):
        """Test when different units are extracted."""
        resolution = resolve_mileage("90000 km", "90000 mi")

        # Same number but different units -> MINOR_FORMATTING
        assert resolution.disagreement_type == "MINOR_FORMATTING"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
