"""
Tests for deal detection — underpriced car identification.

Covers:
1. calculate_segment_stats() — IQR-based statistics from price lists
2. score_offer() — deal score calculation for a single offer
3. API endpoint /api/deals — correct JSON structure and filtering
"""

import pytest
from webapp.deal_detection import calculate_segment_stats, score_offer


class TestCalculateSegmentStats:
    """IQR-based segment statistics from price lists."""

    def test_basic_stats(self):
        """Known distribution should produce correct Q1, median, Q3."""
        prices = [100_000, 120_000, 140_000, 160_000, 180_000,
                  200_000, 220_000, 240_000, 260_000, 280_000]
        stats = calculate_segment_stats(prices)
        assert stats["median"] == 190_000
        assert stats["q1"] <= stats["median"] <= stats["q3"]
        assert stats["count"] == 10
        assert stats["iqr"] == stats["q3"] - stats["q1"]

    def test_single_price(self):
        """Single price — median equals that price, IQR is 0."""
        stats = calculate_segment_stats([150_000])
        assert stats["median"] == 150_000
        assert stats["iqr"] == 0
        assert stats["count"] == 1

    def test_two_prices(self):
        """Two prices — median is their average."""
        stats = calculate_segment_stats([100_000, 200_000])
        assert stats["median"] == 150_000
        assert stats["count"] == 2

    def test_identical_prices(self):
        """All identical prices — IQR is 0, median equals price."""
        stats = calculate_segment_stats([150_000] * 10)
        assert stats["median"] == 150_000
        assert stats["iqr"] == 0

    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        assert calculate_segment_stats([]) is None

    def test_sorted_output(self):
        """Unsorted input should still produce correct stats."""
        prices = [300_000, 100_000, 200_000, 400_000, 500_000]
        stats = calculate_segment_stats(prices)
        assert stats["median"] == 300_000
        assert stats["q1"] < stats["median"]
        assert stats["q3"] > stats["median"]


class TestScoreOffer:
    """Deal score calculation for a single offer against segment stats."""

    def test_underpriced_offer(self):
        """Offer at 50% of median should have ~50% deal score."""
        stats = {"median": 200_000, "q1": 150_000, "q3": 250_000, "iqr": 100_000, "count": 20}
        score = score_offer(100_000, stats)
        assert score == pytest.approx(50.0)

    def test_offer_at_median(self):
        """Offer at median price should have 0% deal score."""
        stats = {"median": 200_000, "q1": 150_000, "q3": 250_000, "iqr": 100_000, "count": 20}
        score = score_offer(200_000, stats)
        assert score == pytest.approx(0.0)

    def test_overpriced_offer(self):
        """Offer above median should have negative score."""
        stats = {"median": 200_000, "q1": 150_000, "q3": 250_000, "iqr": 100_000, "count": 20}
        score = score_offer(300_000, stats)
        assert score == pytest.approx(-50.0)

    def test_very_cheap_offer(self):
        """Offer at 10% of median should have 90% score."""
        stats = {"median": 200_000, "q1": 150_000, "q3": 250_000, "iqr": 100_000, "count": 20}
        score = score_offer(20_000, stats)
        assert score == pytest.approx(90.0)

    def test_zero_median_returns_none(self):
        """Zero median should return None (avoid division by zero)."""
        stats = {"median": 0, "q1": 0, "q3": 0, "iqr": 0, "count": 5}
        assert score_offer(100_000, stats) is None


class TestDealDetectionAPI:
    """Integration tests for /api/deals endpoint."""

    @pytest.fixture
    def client(self):
        """Flask test client."""
        from webapp.app import app
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as client:
            yield client

    def test_deals_endpoint_returns_json(self, client):
        """GET /api/deals should return JSON with deals array."""
        resp = client.get("/api/deals")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "deals" in data
        assert "pagination" in data
        assert isinstance(data["deals"], list)

    def test_deals_with_brand_filter(self, client):
        """Filter by brand should only return matching brand."""
        resp = client.get("/api/deals?brand=skoda")
        assert resp.status_code == 200
        data = resp.get_json()
        for deal in data["deals"]:
            assert deal["brand"] == "skoda"

    def test_deals_pagination(self, client):
        """Pagination params should be respected."""
        resp = client.get("/api/deals?page=1&per_page=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["deals"]) <= 5
        assert data["pagination"]["per_page"] == 5

    def test_deals_min_score_filter(self, client):
        """min_score filter should only return deals above threshold."""
        resp = client.get("/api/deals?min_score=20")
        assert resp.status_code == 200
        data = resp.get_json()
        for deal in data["deals"]:
            assert deal["deal_score"] >= 20

    def test_single_deal_endpoint(self, client):
        """GET /api/deals/<id> should return deal info or 404."""
        resp = client.get("/api/deals/999999999")
        assert resp.status_code in (200, 404)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
