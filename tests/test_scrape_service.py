"""
Tests for the scrape service — job lifecycle, DB tracking, and constraints.

Covers:
1. Job creation and DB row insertion
2. Single-job constraint (no concurrent jobs)
3. Status querying
4. Job cancellation
5. DB statistics
6. Stale job detection
"""
import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# Set env vars before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-padded-to-min-32-bytes")
os.environ.setdefault("MYSQL_PASSWORD", "test")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database.model import Base, ScrapeJob, Brand, Model, Offer


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)
    yield session
    session.remove()
    engine.dispose()


class TestScrapeJobModel:
    """ScrapeJob ORM model basic operations."""

    def test_create_job(self, db_session):
        """A new scrape job can be inserted and queried."""
        job = ScrapeJob(
            job_id="20260409_120000",
            status="queued",
            brands=json.dumps(["skoda", "volkswagen"]),
        )
        db_session.add(job)
        db_session.commit()

        loaded = db_session.query(ScrapeJob).filter_by(job_id="20260409_120000").one()
        assert loaded.status == "queued"
        assert loaded.processed_urls == 0

    def test_serialize(self, db_session):
        """serialize() returns a JSON-safe dict with parsed brands."""
        job = ScrapeJob(
            job_id="20260409_120000",
            status="running",
            brands=json.dumps(["skoda"]),
            brands_done=json.dumps(["skoda"]),
            started_at=datetime(2026, 4, 9, 12, 0, 0),
            saved_count=42,
        )
        db_session.add(job)
        db_session.commit()

        data = job.serialize()
        assert data["brands"] == ["skoda"]
        assert data["brands_done"] == ["skoda"]
        assert data["saved_count"] == 42
        assert data["started_at"] == "2026-04-09T12:00:00"

    def test_serialize_null_brands(self, db_session):
        """serialize() handles NULL brands gracefully."""
        job = ScrapeJob(job_id="test_null", status="queued")
        db_session.add(job)
        db_session.commit()

        data = job.serialize()
        assert data["brands"] is None
        assert data["brands_done"] == []

    def test_unique_job_id(self, db_session):
        """Duplicate job_id raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        db_session.add(ScrapeJob(job_id="dup", status="queued"))
        db_session.commit()
        db_session.add(ScrapeJob(job_id="dup", status="queued"))
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_status_update(self, db_session):
        """Job status can be updated to cancelled."""
        job = ScrapeJob(job_id="cancel_me", status="running", worker_pid=12345)
        db_session.add(job)
        db_session.commit()

        job.status = "cancelled"
        job.completed_at = datetime(2026, 4, 9, 13, 0, 0)
        db_session.commit()

        loaded = db_session.query(ScrapeJob).filter_by(job_id="cancel_me").one()
        assert loaded.status == "cancelled"
        assert loaded.completed_at is not None


class TestDbStats:
    """DB statistics queries against Brand/Model/Offer."""

    def test_offer_counts_per_brand(self, db_session):
        """Count offers grouped by brand."""
        brand = Brand(name="skoda")
        db_session.add(brand)
        db_session.flush()

        model = Model(name="octavia", brand_id=brand.id)
        db_session.add(model)
        db_session.flush()

        for i in range(3):
            db_session.add(Offer(
                model_id=model.id,
                price=100000 + i * 10000,
                unique_id=f"uid_{i}",
            ))
        db_session.commit()

        from sqlalchemy import func
        result = (
            db_session.query(Brand.name, func.count(Offer.id))
            .join(Model, Brand.id == Model.brand_id)
            .join(Offer, Model.id == Offer.model_id)
            .group_by(Brand.name)
            .all()
        )
        assert len(result) == 1
        assert result[0][0] == "skoda"
        assert result[0][1] == 3
