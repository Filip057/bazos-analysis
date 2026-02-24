"""
Unit tests for Generic Entity Feedback Verification System

Tests power, mileage, and fuel verification using the EntityFeedbackVerifier.
"""

import pytest
from unittest.mock import MagicMock
from ml.entity_feedback_verifier import EntityFeedbackVerifier, EntityVerification


def make_ml_extractor(year=None, mileage=None, power=None, fuel=None):
    """Create a mock ML extractor with predefined return value."""
    mock = MagicMock()
    mock.extract.return_value = {
        'year': year,
        'mileage': mileage,
        'power': power,
        'fuel': fuel,
    }
    return mock


# =============================================================================
# POWER VERIFICATION TESTS
# =============================================================================

class TestPowerValidation:
    """Power must pass validation before ML is asked."""

    def test_rejects_power_below_valid_range(self):
        """Power below 30 kW is invalid."""
        ml = make_ml_extractor(power=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 15 kW", 'power', "15 kW", 'medium')

        assert result.verified is False
        assert result.confidence == 0.0
        assert result.method == "REJECTED_INVALID_POWER"
        ml.extract.assert_not_called()

    def test_rejects_power_above_valid_range(self):
        """Power above 500 kW is invalid for regular cars."""
        ml = make_ml_extractor(power=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 600 kW", 'power', "600 kW", 'high')

        assert result.verified is False
        assert result.method == "REJECTED_INVALID_POWER"

    def test_accepts_power_in_valid_range(self):
        """Power 30-500 kW is valid range."""
        ml = make_ml_extractor(power="145 kW")  # ML confirms
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda 145 kW diesel", 'power', "145 kW", 'high')

        assert result.verified is True
        assert result.confidence >= 0.65


class TestPowerConfidenceMatrix:
    """Test confidence calculation for power verification."""

    def test_high_regex_ml_confirms_power(self):
        """výkon 145 kW + ML confirms → highest confidence."""
        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia, výkon 145 kW, diesel",
            'power',
            "145 kW",
            'high'
        )

        assert result.confidence == 0.95
        assert result.method == "ML_CONFIRMED_HIGH_REGEX_POWER"
        assert result.ml_confirmed is True
        assert result.verified is True

    def test_high_regex_ml_misses_power(self):
        """High regex power without ML confirmation → still accepted."""
        ml = make_ml_extractor(power=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia, výkon 145 kW, diesel",
            'power',
            "145 kW",
            'high'
        )

        assert result.confidence == 0.80
        assert result.method == "HIGH_REGEX_ACCEPTED_POWER"
        assert result.verified is True

    def test_medium_regex_ml_confirms_power(self):
        """Medium regex + ML confirms → high confidence."""
        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, 145 kW, diesel",
            'power',
            "145 kW",
            'medium'
        )

        assert result.confidence == 0.85
        assert result.method == "ML_CONFIRMED_MEDIUM_REGEX_POWER"
        assert result.verified is True

    def test_medium_regex_ml_misses_power(self):
        """Medium regex without ML confirmation → uncertain."""
        ml = make_ml_extractor(power=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, 145 kW, diesel",
            'power',
            "145 kW",
            'medium'
        )

        assert result.confidence == 0.55
        assert result.method == "MEDIUM_REGEX_UNCERTAIN_POWER"
        assert result.verified is False

    def test_low_regex_ml_confirms_power(self):
        """Low regex + ML confirms → accepted with medium confidence."""
        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "prodám auto 145 kW benzin",
            'power',
            "145 kW",
            'low'
        )

        assert result.confidence == 0.70
        assert result.method == "ML_CONFIRMED_LOW_REGEX_POWER"
        assert result.verified is True

    def test_low_regex_ml_misses_power(self):
        """Low regex, no ML confirmation → rejected."""
        ml = make_ml_extractor(power=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "prodám auto 145 kW",
            'power',
            "145 kW",
            'low'
        )

        assert result.confidence == 0.30
        assert result.method == "REGEX_ONLY_UNVERIFIED_POWER"
        assert result.verified is False


class TestPowerNumericMatching:
    """Power comparison is numeric: 145 kW == 145 kW."""

    def test_power_numeric_comparison(self):
        """145 kW from ML matches 145 kW from regex."""
        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 145 kW", 'power', "145 kW", 'medium')

        assert result.ml_confirmed is True

    def test_power_different_values_not_confirmed(self):
        """ML finds 145 kW, regex finds 110 kW → not confirmed."""
        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 110 kW diesel", 'power', "110 kW", 'medium')

        assert result.ml_confirmed is False


# =============================================================================
# MILEAGE VERIFICATION TESTS
# =============================================================================

class TestMileageValidation:
    """Mileage must pass validation before ML is asked."""

    def test_rejects_negative_mileage(self):
        """Negative mileage is invalid."""
        ml = make_ml_extractor(mileage=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto", 'mileage', "-5000 km", 'medium')

        # Will fail numeric extraction
        assert result.verified is False

    def test_accepts_mileage_in_valid_range(self):
        """0 to 1,000,000 km is valid."""
        ml = make_ml_extractor(mileage="90000 km")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda 90000 km", 'mileage', "90000 km", 'high')

        assert result.verified is True


class TestMileageConfidenceMatrix:
    """Test confidence calculation for mileage verification."""

    def test_high_regex_ml_confirms_mileage(self):
        """najeto 90000 km + ML confirms → highest confidence."""
        ml = make_ml_extractor(mileage="90000 km")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia, najeto 90000 km, diesel",
            'mileage',
            "90000 km",
            'high'
        )

        assert result.confidence == 0.95
        assert result.method == "ML_CONFIRMED_HIGH_REGEX_MILEAGE"
        assert result.verified is True

    def test_medium_regex_ml_misses_mileage(self):
        """Medium regex without ML confirmation → uncertain."""
        ml = make_ml_extractor(mileage=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, 90000 km, diesel",
            'mileage',
            "90000 km",
            'medium'
        )

        assert result.confidence == 0.55
        assert result.verified is False

    def test_low_regex_ml_confirms_mileage(self):
        """Low regex + ML confirms → accepted."""
        ml = make_ml_extractor(mileage="90000 km")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "prodám auto 90000 diesel",
            'mileage',
            "90000 km",
            'low'
        )

        assert result.confidence == 0.70
        assert result.verified is True


class TestMileageNumericMatching:
    """Mileage comparison is numeric."""

    def test_mileage_numeric_comparison(self):
        """90000 km from ML matches 90000 km from regex."""
        ml = make_ml_extractor(mileage="90000 km")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 90000 km", 'mileage', "90000 km", 'medium')

        assert result.ml_confirmed is True

    def test_mileage_formatting_variations(self):
        """90000 vs 90 000 vs 90.000 – all the same numerically."""
        ml = make_ml_extractor(mileage="90000")
        verifier = EntityFeedbackVerifier(ml)

        # Regex found "90 000 km", ML returns "90000"
        result = verifier.verify("najeto 90 000 km", 'mileage', "90000 km", 'high')
        assert result.ml_confirmed is True


# =============================================================================
# FUEL VERIFICATION TESTS
# =============================================================================

class TestFuelValidation:
    """Fuel must be a recognized fuel type."""

    def test_accepts_diesel(self):
        """diesel is a valid fuel type."""
        ml = make_ml_extractor(fuel="diesel")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda diesel", 'fuel', "diesel", 'medium')

        assert result.verified is True

    def test_accepts_benzin(self):
        """benzín is a valid fuel type."""
        ml = make_ml_extractor(fuel="benzín")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda benzín", 'fuel', "benzín", 'medium')

        assert result.verified is True

    def test_rejects_invalid_fuel(self):
        """Invalid fuel string is rejected."""
        ml = make_ml_extractor(fuel=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda", 'fuel', "xyz123", 'medium')

        assert result.verified is False
        assert result.method == "REJECTED_INVALID_FUEL"


class TestFuelConfidenceMatrix:
    """Test confidence calculation for fuel verification."""

    def test_high_regex_ml_confirms_fuel(self):
        """High regex fuel + ML confirms → highest confidence."""
        ml = make_ml_extractor(fuel="diesel")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, diesel, 90000 km",
            'fuel',
            "diesel",
            'high'
        )

        assert result.confidence == 0.95
        assert result.verified is True

    def test_medium_regex_ml_confirms_fuel(self):
        """Medium regex + ML confirms → high confidence."""
        ml = make_ml_extractor(fuel="diesel")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia diesel",
            'fuel',
            "diesel",
            'medium'
        )

        assert result.confidence == 0.85
        assert result.verified is True

    def test_low_regex_ml_misses_fuel(self):
        """Low regex, no ML confirmation → rejected."""
        ml = make_ml_extractor(fuel=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "auto diesel",
            'fuel',
            "diesel",
            'low'
        )

        assert result.confidence == 0.30
        assert result.verified is False


class TestFuelTextMatching:
    """Fuel comparison is text-based, case-insensitive."""

    def test_fuel_case_insensitive(self):
        """DIESEL == diesel."""
        ml = make_ml_extractor(fuel="Diesel")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda DIESEL", 'fuel', "diesel", 'medium')

        assert result.ml_confirmed is True

    def test_fuel_different_types_not_confirmed(self):
        """diesel != benzín."""
        ml = make_ml_extractor(fuel="benzín")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("Škoda diesel", 'fuel', "diesel", 'medium')

        assert result.ml_confirmed is False


# =============================================================================
# CONTEXT WINDOW TESTS
# =============================================================================

class TestContextWindow:
    """ML is called with a context window, not the full text."""

    def test_ml_receives_context_window_power(self):
        """ML receives trimmed context for power."""
        full_text = "A" * 200 + "145 kW" + "B" * 200

        ml = make_ml_extractor(power=None)
        verifier = EntityFeedbackVerifier(ml)
        verifier.verify(full_text, 'power', "145 kW", 'medium')

        called_with = ml.extract.call_args[0][0]
        assert len(called_with) < len(full_text)
        assert "145 kW" in called_with

    def test_context_contains_candidate(self):
        """Context passed to ML must contain the candidate."""
        text = "Škoda Octavia 2015, 145 kW, diesel, 90000 km"

        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(text, 'power', "145 kW", 'medium')

        assert "145 kW" in result.context_text


# =============================================================================
# METADATA & SERIALIZATION TESTS
# =============================================================================

class TestEntityVerificationMetadata:
    """Check that EntityVerification contains useful metadata."""

    def test_entity_type_preserved(self):
        """entity_type should be stored."""
        ml = make_ml_extractor(power="145 kW")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 145 kW", 'power', "145 kW", 'high')

        assert result.entity_type == 'power'

    def test_candidate_value_preserved(self):
        """candidate_value should be the original regex string."""
        ml = make_ml_extractor(mileage="90000 km")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto 90000 km", 'mileage', "90000 km", 'medium')

        assert result.candidate_value == "90000 km"

    def test_to_dict(self):
        """to_dict() should return a serializable dictionary."""
        ml = make_ml_extractor(fuel="diesel")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify("auto diesel", 'fuel', "diesel", 'medium')
        d = result.to_dict()

        assert isinstance(d, dict)
        assert d['entity_type'] == 'fuel'
        assert d['candidate_value'] == "diesel"
        assert 'confidence' in d
        assert 'verified' in d


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error scenarios and edge cases."""

    def test_unsupported_entity_type(self):
        """Unsupported entity type raises ValueError."""
        ml = make_ml_extractor()
        verifier = EntityFeedbackVerifier(ml)

        with pytest.raises(ValueError, match="Unsupported entity_type"):
            verifier.verify("auto", 'unsupported_type', "value", 'medium')

    def test_ml_error_handled_gracefully(self):
        """If ML throws an exception, treat as 'not confirmed'."""
        ml = MagicMock()
        ml.extract.side_effect = Exception("model crashed")
        verifier = EntityFeedbackVerifier(ml)

        result = verifier.verify("auto 145 kW", 'power', "145 kW", 'high')

        # ML error → ml_confirmed=False, but high regex still accepts
        assert result.ml_confirmed is False
        assert result.method == "HIGH_REGEX_ACCEPTED_POWER"
        assert result.verified is True


# =============================================================================
# REAL-WORLD SCENARIO TESTS
# =============================================================================

class TestRealWorldScenarios:
    """Realistic car listing scenarios."""

    def test_power_only_regex_found(self):
        """ML misses power 145 kW, regex finds it, ML feedback confirms."""
        ml = make_ml_extractor(power="145 kW", mileage=None, fuel=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, výkon 145 kW, diesel, dobrý stav",
            'power',
            "145 kW",
            'high'
        )

        assert result.verified is True
        assert result.confidence >= 0.90

    def test_mileage_only_regex_found(self):
        """ML misses mileage, regex finds it, ML feedback confirms."""
        ml = make_ml_extractor(power=None, mileage="90000 km", fuel=None)
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia najeto 90000 km diesel",
            'mileage',
            "90000 km",
            'high'
        )

        assert result.verified is True

    def test_fuel_only_regex_found(self):
        """ML misses fuel, regex finds diesel, ML feedback confirms."""
        ml = make_ml_extractor(power=None, mileage=None, fuel="diesel")
        verifier = EntityFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015 diesel zachovalý stav",
            'fuel',
            "diesel",
            'medium'
        )

        assert result.verified is True
        assert result.confidence == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
