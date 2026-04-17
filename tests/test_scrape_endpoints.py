"""
Tests for the scraping control API endpoints.

Covers:
1. Auth enforcement (401 without token)
2. Start scrape → 202
3. Status endpoint
4. Cancel endpoint
5. Conflict when job already running
6. DB stats endpoint
"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-padded-to-min-32-bytes")
os.environ.setdefault("MYSQL_PASSWORD", "test")

from webapp.auth import issue_token


@pytest.fixture
def app():
    """Create Flask test app with mocked DB."""
    with patch("webapp.app.init_database"):
        with patch("webapp.app.create_engine") as mock_engine:
            mock_engine.return_value = MagicMock()
            # Re-import to get fresh app with mocks
            import importlib
            import webapp.app as app_module
            importlib.reload(app_module)
            app_module.app.config["TESTING"] = True
            yield app_module.app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def admin_headers():
    """Authorization headers with valid admin JWT."""
    token = issue_token(admin_id=1, username="testadmin")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestScrapeEndpointAuth:
    """All scraping endpoints require admin auth."""

    def test_start_requires_auth(self, client):
        """POST /api/admin/scrape/start returns 401 without token."""
        resp = client.post("/api/admin/scrape/start", json={"brands": ["skoda"]})
        assert resp.status_code == 401

    def test_status_requires_auth(self, client):
        """GET /api/admin/scrape/status returns 401 without token."""
        resp = client.get("/api/admin/scrape/status")
        assert resp.status_code == 401

    def test_cancel_requires_auth(self, client):
        """POST /api/admin/scrape/cancel returns 401 without token."""
        resp = client.post("/api/admin/scrape/cancel", json={"job_id": "test"})
        assert resp.status_code == 401

    def test_db_stats_requires_auth(self, client):
        """GET /api/admin/scrape/db-stats returns 401 without token."""
        resp = client.get("/api/admin/scrape/db-stats")
        assert resp.status_code == 401


class TestScrapeStartEndpoint:
    """POST /api/admin/scrape/start."""

    @patch("webapp.app.scrape_manager")
    def test_start_returns_202(self, mock_manager, client, admin_headers):
        """Successful start returns 202 with job_id."""
        mock_manager.start_job.return_value = {
            "job_id": "20260409_120000",
            "status": "queued",
        }
        resp = client.post(
            "/api/admin/scrape/start",
            headers=admin_headers,
            json={"brands": ["skoda"]},
        )
        assert resp.status_code == 202
        data = resp.get_json()
        assert data["job_id"] == "20260409_120000"

    @patch("webapp.app.scrape_manager")
    def test_start_conflict(self, mock_manager, client, admin_headers):
        """Returns 409 when a job is already running."""
        mock_manager.start_job.return_value = None
        resp = client.post(
            "/api/admin/scrape/start",
            headers=admin_headers,
            json={"brands": ["skoda"]},
        )
        assert resp.status_code == 409


class TestScrapeStatusEndpoint:
    """GET /api/admin/scrape/status."""

    @patch("webapp.app.scrape_manager")
    def test_status_returns_job(self, mock_manager, client, admin_headers):
        """Returns current job status."""
        mock_manager.get_active_job.return_value = {
            "job_id": "20260409_120000",
            "status": "running",
            "current_brand": "skoda",
            "processed_urls": 50,
            "saved_count": 40,
        }
        resp = client.get("/api/admin/scrape/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["job"]["status"] == "running"

    @patch("webapp.app.scrape_manager")
    def test_status_no_job(self, mock_manager, client, admin_headers):
        """Returns null job when nothing is running."""
        mock_manager.get_active_job.return_value = None
        resp = client.get("/api/admin/scrape/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["job"] is None


class TestScrapeCancelEndpoint:
    """POST /api/admin/scrape/cancel."""

    @patch("webapp.app.scrape_manager")
    def test_cancel_returns_ok(self, mock_manager, client, admin_headers):
        """Successful cancel returns ok."""
        mock_manager.cancel_job.return_value = True
        resp = client.post(
            "/api/admin/scrape/cancel",
            headers=admin_headers,
            json={"job_id": "20260409_120000"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    @patch("webapp.app.scrape_manager")
    def test_cancel_not_found(self, mock_manager, client, admin_headers):
        """Cancel of non-existent job returns 404."""
        mock_manager.cancel_job.return_value = False
        resp = client.post(
            "/api/admin/scrape/cancel",
            headers=admin_headers,
            json={"job_id": "nonexistent"},
        )
        assert resp.status_code == 404
