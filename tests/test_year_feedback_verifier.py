"""
Unit tests for Year Feedback Verification System

Tests the scenario: ML = None, Regex = found year
"""

import pytest
from unittest.mock import MagicMock
from ml.year_feedback_verifier import YearFeedbackVerifier, YearVerification


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


class TestYearVerificationBasicSanity:
    """Year must pass a basic validity check before ML is even asked."""

    def test_rejects_year_before_range(self):
        """Years before 1985 are not valid car years."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("auto z roku 1950", "1950", regex_confidence='high')

        assert result.verified is False
        assert result.confidence == 0.0
        assert result.method == "REJECTED_INVALID_YEAR"
        ml.extract.assert_not_called()  # ML should not be called

    def test_rejects_year_after_range(self):
        """Years far in the future are not valid."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("model 2099", "2099", regex_confidence='high')

        assert result.verified is False
        assert result.confidence == 0.0
        assert result.method == "REJECTED_INVALID_YEAR"

    def test_rejects_non_year_string(self):
        """Non-year string should be rejected immediately."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("najeto 90000 km", "abcd", regex_confidence='medium')

        assert result.verified is False
        assert result.method == "REJECTED_INVALID_YEAR"


class TestConfidenceMatrix:
    """
    The core logic: confidence depends on (regex_confidence, ml_confirmed).
    """

    def test_high_regex_ml_confirms(self):
        """rok výroby 2015 found by regex + ML confirms → highest confidence."""
        ml = make_ml_extractor(year="2015")  # ML confirms
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "rok výroby 2015, najeto 90 000 km",
            "2015",
            regex_confidence='high'
        )

        assert result.confidence == 0.95
        assert result.method == "ML_CONFIRMED_HIGH_REGEX"
        assert result.ml_confirmed is True
        assert result.verified is True

    def test_high_regex_ml_misses(self):
        """rok výroby 2015 found by regex, ML doesn't confirm → still accepted."""
        ml = make_ml_extractor(year=None)  # ML doesn't confirm
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "rok výroby 2015, najeto 90 000 km",
            "2015",
            regex_confidence='high'
        )

        assert result.confidence == 0.80
        assert result.method == "HIGH_REGEX_ACCEPTED"
        assert result.ml_confirmed is False
        assert result.verified is True  # Still accepted

    def test_medium_regex_ml_confirms(self):
        """Škoda Octavia 2015 style + ML confirms → high confidence."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, 90000 km, diesel",
            "2015",
            regex_confidence='medium'
        )

        assert result.confidence == 0.85
        assert result.method == "ML_CONFIRMED_MEDIUM_REGEX"
        assert result.verified is True

    def test_medium_regex_ml_misses(self):
        """Medium regex without ML confirmation → uncertain, below threshold."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, 90000 km, diesel",
            "2015",
            regex_confidence='medium'
        )

        assert result.confidence == 0.55
        assert result.method == "MEDIUM_REGEX_UNCERTAIN"
        assert result.verified is False  # Below threshold 0.65

    def test_low_regex_ml_confirms(self):
        """Standalone year + ML confirms → accepted but with medium confidence."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "prodám auto, 2015, 90000 km, nafta",
            "2015",
            regex_confidence='low'
        )

        assert result.confidence == 0.70
        assert result.method == "ML_CONFIRMED_LOW_REGEX"
        assert result.verified is True

    def test_low_regex_ml_misses(self):
        """Standalone year, no ML confirmation → rejected."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "prodám auto, 2015, 90000 km",
            "2015",
            regex_confidence='low'
        )

        assert result.confidence == 0.30
        assert result.method == "REGEX_ONLY_UNVERIFIED"
        assert result.verified is False


class TestMlContextWindow:
    """ML is called with a context window, not the full text."""

    def test_ml_receives_context_window(self):
        """ML should receive a trimmed context around the year, not the full text."""
        full_text = "A" * 200 + "2015" + "B" * 200  # Long text

        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml, confidence_threshold=0.65)
        verifier.verify(full_text, "2015", regex_confidence='medium')

        # ML should have been called with a shorter context
        called_with = ml.extract.call_args[0][0]
        assert len(called_with) < len(full_text)
        assert "2015" in called_with

    def test_ml_called_with_year_in_context(self):
        """The context passed to ML must contain the candidate year."""
        text = "Prodám Škoda Octavia 2015, najeto 90000 km, diesel, STK 2027"

        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        verifier.verify(text, "2015", regex_confidence='medium')

        called_with = ml.extract.call_args[0][0]
        assert "2015" in called_with

    def test_ml_year_matched_numerically(self):
        """ML can return "2015" or " 2015" – numeric comparison is used."""
        ml = make_ml_extractor(year=" 2015 ")  # Extra whitespace
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, najeto 90000 km",
            "2015",
            regex_confidence='medium'
        )

        assert result.ml_confirmed is True

    def test_ml_different_year_not_confirmed(self):
        """If ML finds a different year, it's NOT a confirmation."""
        ml = make_ml_extractor(year="2018")  # Different year
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia 2015, najeto 90000 km",
            "2015",
            regex_confidence='medium'
        )

        assert result.ml_confirmed is False


class TestVerificationMetadata:
    """Check that YearVerification contains useful metadata."""

    def test_candidate_year_preserved(self):
        """candidate_year should be the original regex string."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("Škoda 2015 diesel", "2015", regex_confidence='high')

        assert result.candidate_year == "2015"

    def test_regex_confidence_preserved(self):
        """regex_confidence should be stored in the result."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("Škoda 2015 diesel", "2015", regex_confidence='high')

        assert result.regex_confidence == 'high'

    def test_context_text_populated(self):
        """context_text should contain the text window shown to ML."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("Škoda Octavia 2015, najeto 90000 km", "2015", regex_confidence='medium')

        assert "2015" in result.context_text
        assert len(result.context_text) > 0

    def test_to_dict(self):
        """to_dict() should return a serializable dictionary."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify("Škoda 2015", "2015", regex_confidence='medium')
        d = result.to_dict()

        assert isinstance(d, dict)
        assert d['candidate_year'] == "2015"
        assert 'confidence' in d
        assert 'verified' in d
        assert 'method' in d
        assert 'ml_confirmed' in d


class TestRealWorldScenarios:
    """Realistic car listing scenarios."""

    def test_rok_vyroby_ml_confirms(self):
        """Classic 'rok výroby 2015' – regex high confidence, ML confirms."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda Octavia, rok výroby 2015, najeto 90000 km, diesel, STK do 2027",
            "2015",
            regex_confidence='high'
        )

        assert result.verified is True
        assert result.candidate_year == "2015"
        assert result.confidence >= 0.90

    def test_standalone_year_no_ml_confirmation(self):
        """Standalone year number without context – ML doesn't confirm → reject."""
        ml = make_ml_extractor(year=None)
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Golf 4, 2003, 180000, benzin",
            "2003",
            regex_confidence='low'
        )

        assert result.verified is False

    def test_brand_model_year_ml_confirms(self):
        """'Škoda Octavia 2015' style – ML feedback confirms."""
        ml = make_ml_extractor(year="2015")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Prodám Škoda Octavia 2015 diesel, zachovalý stav",
            "2015",
            regex_confidence='medium'
        )

        assert result.verified is True
        assert result.confidence == 0.85

    def test_ml_error_handled_gracefully(self):
        """If ML throws an exception, it's treated as 'not confirmed'."""
        ml = MagicMock()
        ml.extract.side_effect = Exception("model crashed")
        verifier = YearFeedbackVerifier(ml)
        result = verifier.verify(
            "Škoda 2015 diesel",
            "2015",
            regex_confidence='high'
        )

        # ML error → ml_confirmed=False, but high regex confidence still accepts
        assert result.ml_confirmed is False
        assert result.method == "HIGH_REGEX_ACCEPTED"
        assert result.verified is True


class TestTwoDigitYearExpansion:
    """Test 2-digit year handling in regex patterns."""

    def test_two_digit_year_rv09(self):
        """'r.v. 09' should expand to 2009."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Škoda Fabia r.v. 09, najeto 120000 km")
        assert len(matches) >= 1
        assert matches[0].value == 2009

    def test_two_digit_year_rv96(self):
        """'rv96' should expand to 1996."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Ford Escort rv96, benzín")
        assert len(matches) >= 1
        assert matches[0].value == 1996

    def test_two_digit_year_rok_vyroby_03(self):
        """'rok výroby 03' should expand to 2003."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Renault Clio rok výroby 03")
        assert len(matches) >= 1
        assert matches[0].value == 2003

    def test_two_digit_year_high_confidence(self):
        """2-digit year with r.v. context should be HIGH confidence."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Opel Astra r.v. 15, diesel")
        assert len(matches) >= 1
        assert matches[0].confidence == 'high'
        assert matches[0].value == 2015

    def test_two_digit_year_too_old_rejected(self):
        """'r.v. 85' → 1985, below YEAR_MIN=1990 → rejected."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Trabant r.v. 85")
        assert len(matches) == 0


class TestYearRangeValidation:
    """Test that impossible years are rejected everywhere."""

    def test_peugeot_5008_not_a_year(self):
        """Model number 5008 should NOT be extracted as a year."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Peugeot 5008 1.6 BlueHDi")
        # 5008 is way outside 1990-2027 range
        year_values = [m.value for m in matches]
        assert 5008 not in year_values

    def test_peugeot_2008_ambiguity(self):
        """'Peugeot 2008' — 2008 is within year range but is a model name.
        Without year context, it should only be LOW confidence at best."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Peugeot 2008 1.2 PureTech")
        # If matched, it should be low confidence (standalone pattern)
        for m in matches:
            if m.value == 2008:
                assert m.confidence == 'low'

    def test_future_year_rejected(self):
        """Year 2099 should be rejected by all layers."""
        from ml.context_aware_patterns import ContextAwarePatterns
        patterns = ContextAwarePatterns()
        matches = patterns.find_years("Auto rok výroby 2099")
        assert len(matches) == 0

    def test_normalize_year_rejects_future(self):
        """normalize_year should reject years beyond current+1."""
        from ml.production_extractor import DataNormalizer
        assert DataNormalizer.normalize_year(2099) is None
        assert DataNormalizer.normalize_year(5008) is None

    def test_normalize_year_accepts_valid(self):
        """normalize_year should accept valid years."""
        from ml.production_extractor import DataNormalizer
        assert DataNormalizer.normalize_year(2015) == 2015
        assert DataNormalizer.normalize_year("2020") == 2020
        assert DataNormalizer.normalize_year(1995) == 1995

    def test_normalize_year_rejects_pre_1990(self):
        """normalize_year should reject years before 1990."""
        from ml.production_extractor import DataNormalizer
        assert DataNormalizer.normalize_year(1985) is None
        assert DataNormalizer.normalize_year(1900) is None

    def test_db_validate_year(self):
        """Database layer should reject invalid years."""
        from scraper.database_operations import validate_year
        assert validate_year(2015) == 2015
        assert validate_year(5008) is None
        assert validate_year(2099) is None
        assert validate_year(1989) is None
        assert validate_year(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
