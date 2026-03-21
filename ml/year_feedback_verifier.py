"""
Year Feedback Verification System
===================================

When the ML model does NOT find a year but regex DOES, this module
creates a feedback loop: regex candidate is sent back to the ML model
which verifies it in a focused context window.

Triggered ONLY when: ML year = None, Regex year = found

Flow:
  1. Regex finds "2015" in text
  2. YearFeedbackVerifier extracts a context window around "2015"
  3. ML is asked: "is there a year in this context?"
  4. If ML confirms → high confidence, accept the year
  5. If ML doesn't confirm → confidence depends on regex confidence level

Confidence matrix:
  ┌──────────────────┬──────────────┬──────────────┐
  │ Regex confidence │ ML confirms  │  Final conf. │
  ├──────────────────┼──────────────┼──────────────┤
  │ high             │ yes          │ 0.95 ✓       │
  │ high             │ no           │ 0.80 ✓       │  ← "rok výroby" is reliable
  │ medium           │ yes          │ 0.85 ✓       │
  │ medium           │ no           │ 0.55 ?       │  ← uncertain
  │ low              │ yes          │ 0.70 ✓       │
  │ low              │ no           │ 0.30 ✗       │  ← rejected
  └──────────────────┴──────────────┴──────────────┘
"""

import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class YearVerification:
    """
    Complete year verification result with metadata.

    Structure:
    - candidate_year: The regex-found year string (e.g., "2015")
    - regex_confidence: How confident the regex was ('high', 'medium', 'low')
    - ml_confirmed: Did ML find the same year in the context window?
    - confidence: Final combined confidence score (0.0–1.0)
    - verified: True if confidence >= threshold (ready to use)
    - method: Short description of how the decision was made
    - context_text: The text window that was shown to the ML
    """
    candidate_year: str
    regex_confidence: str
    ml_confirmed: bool
    confidence: float
    verified: bool
    method: str
    context_text: str

    def to_dict(self) -> dict:
        return asdict(self)


class YearFeedbackVerifier:
    """
    Verifies regex-found years using ML as a second opinion.

    Only used when ML = None, Regex = found year.

    Example:
        verifier = YearFeedbackVerifier(ml_extractor)
        result = verifier.verify(
            text="Prodám Škoda Octavia 2015, najeto 90000 km",
            regex_candidate="2015",
            regex_confidence="medium"
        )
        if result.verified:
            year = result.candidate_year   # "2015"
    """

    CONFIDENCE_THRESHOLD = 0.65

    # Context window around candidate year for ML verification (chars)
    CONTEXT_WINDOW = 60

    # Valid car year range (dynamic max)
    YEAR_MIN = 1990
    YEAR_MAX = datetime.now().year + 1

    def __init__(self, ml_extractor, confidence_threshold: float = 0.65):
        """
        Args:
            ml_extractor: CarDataExtractor instance (already loaded)
            confidence_threshold: Minimum confidence to mark as verified
        """
        self.ml_extractor = ml_extractor
        self.confidence_threshold = confidence_threshold

    def verify(
        self,
        text: str,
        regex_candidate: str,
        regex_confidence: str = 'low'
    ) -> YearVerification:
        """
        Verify if a regex-found year is a genuine year of manufacture.

        Args:
            text: Original car listing text
            regex_candidate: Year string found by regex, e.g. "2015"
            regex_confidence: Regex confidence level: 'high', 'medium', 'low'

        Returns:
            YearVerification with confidence score and all metadata
        """
        # 1. Basic sanity check – is it even a plausible car year?
        year_int = self._extract_year_int(regex_candidate)
        if year_int is None or not (self.YEAR_MIN <= year_int <= self.YEAR_MAX):
            return YearVerification(
                candidate_year=regex_candidate,
                regex_confidence=regex_confidence,
                ml_confirmed=False,
                confidence=0.0,
                verified=False,
                method="REJECTED_INVALID_YEAR",
                context_text=""
            )

        # 2. Extract context window around the candidate in the original text
        context_text = self._extract_context(text, regex_candidate)

        # 3. Ask ML: is there a YEAR entity in this focused context?
        ml_confirmed = self._ask_ml_to_verify(context_text, regex_candidate)

        # 4. Combine regex confidence + ML answer → final confidence
        confidence, method = self._calculate_confidence(regex_confidence, ml_confirmed)

        return YearVerification(
            candidate_year=regex_candidate,
            regex_confidence=regex_confidence,
            ml_confirmed=ml_confirmed,
            confidence=confidence,
            verified=confidence >= self.confidence_threshold,
            method=method,
            context_text=context_text
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_year_int(self, candidate: str) -> Optional[int]:
        """Extract integer year from a string like '2015'."""
        match = re.search(r'(\d{4})', candidate)
        return int(match.group(1)) if match else None

    def _extract_context(self, text: str, candidate: str) -> str:
        """
        Extract a focused context window around the candidate year.

        Returns a substring of `text` containing the candidate plus
        CONTEXT_WINDOW characters on each side.
        """
        pos = text.find(candidate)
        if pos == -1:
            pos = text.lower().find(candidate.lower())
        if pos == -1:
            # Can't locate it – return the full text (unlikely scenario)
            return text

        start = max(0, pos - self.CONTEXT_WINDOW)
        end = min(len(text), pos + len(candidate) + self.CONTEXT_WINDOW)
        return text[start:end]

    def _ask_ml_to_verify(self, context_text: str, candidate: str) -> bool:
        """
        Run the ML model on the context window and check whether it
        recognises the same year as a YEAR entity.

        Returns True if ML found the same year.
        """
        try:
            ml_result = self.ml_extractor.extract(context_text)
            ml_year = ml_result.get('year')
            if ml_year is None:
                return False

            candidate_int = self._extract_year_int(candidate)
            ml_year_int = self._extract_year_int(ml_year)

            return (
                candidate_int is not None
                and ml_year_int is not None
                and candidate_int == ml_year_int
            )
        except Exception:
            return False

    def _calculate_confidence(
        self,
        regex_confidence: str,
        ml_confirmed: bool
    ) -> tuple:
        """
        Combine regex confidence level and ML confirmation into a
        final score and a human-readable method label.

        Returns: (confidence: float, method: str)
        """
        if regex_confidence == 'high' and ml_confirmed:
            return 0.95, "ML_CONFIRMED_HIGH_REGEX"

        if regex_confidence == 'high' and not ml_confirmed:
            # "rok výroby 2015" style patterns are reliable on their own
            return 0.80, "HIGH_REGEX_ACCEPTED"

        if regex_confidence == 'medium' and ml_confirmed:
            return 0.85, "ML_CONFIRMED_MEDIUM_REGEX"

        if regex_confidence == 'medium' and not ml_confirmed:
            return 0.55, "MEDIUM_REGEX_UNCERTAIN"

        if regex_confidence == 'low' and ml_confirmed:
            return 0.70, "ML_CONFIRMED_LOW_REGEX"

        # low regex, ML doesn't confirm → not trustworthy
        return 0.30, "REGEX_ONLY_UNVERIFIED"
