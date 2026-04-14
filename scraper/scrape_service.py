"""
Scrape Service — bridge between the Flask admin UI and the async pipeline.

Manages scraping job lifecycle via the scrape_jobs DB table so that any
gunicorn worker can read the current status.  The actual scraping runs in
a background thread using ``asyncio.run()`` and the existing PipelineRunner.

Thread-safety:
    - Only one scraping job may run at a time (enforced by DB check).
    - The background thread creates its **own** SQLAlchemy engine/session
      (not the Flask scoped_session) to avoid cross-thread issues.
    - ``worker_pid`` is recorded so stale "running" rows from dead workers
      can be detected and cleaned up.
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, scoped_session

from database.model import Base, ScrapeJob, Brand, Model, Offer
from scraper.data_scrap import CAR_BRANDS
from webapp.config import get_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_factory():
    """Build a standalone SQLAlchemy session factory for background threads."""
    config = get_config()
    engine = create_engine(
        config.DATABASE_URI,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    return scoped_session(sessionmaker(bind=engine)), engine


def _is_pid_alive(pid: int) -> bool:
    """Check whether a given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ---------------------------------------------------------------------------
# ScrapeJobManager
# ---------------------------------------------------------------------------

class ScrapeJobManager:
    """
    Manages scrape job lifecycle with DB-backed state.

    All public methods are safe to call from any gunicorn worker.
    """

    def __init__(self) -> None:
        self._cancel_events: Dict[str, threading.Event] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_job(self, brands: Optional[List[str]] = None) -> Optional[dict]:
        """
        Start a new scraping job in a background thread.

        Returns the job dict on success, or None if a job is already running.
        """
        Session, engine = _make_session_factory()
        session = Session()
        try:
            # Clean stale jobs first
            self._cleanup_stale_jobs(session)

            # Check for already-running job
            active = (
                session.query(ScrapeJob)
                .filter(ScrapeJob.status.in_(["queued", "running"]))
                .first()
            )
            if active is not None:
                return None  # conflict

            job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            job = ScrapeJob(
                job_id=job_id,
                status="queued",
                brands=json.dumps(brands) if brands else json.dumps("all"),
                started_at=datetime.now(),
                worker_pid=os.getpid(),
                brands_done=json.dumps([]),
            )
            session.add(job)
            session.commit()

            result = job.serialize()
        finally:
            Session.remove()
            engine.dispose()

        # Set up cancel event and launch thread
        cancel_event = threading.Event()
        self._cancel_events[job_id] = cancel_event

        thread = threading.Thread(
            target=self._run_in_thread,
            args=(job_id, brands, cancel_event),
            daemon=True,
            name=f"scrape-{job_id}",
        )
        thread.start()
        logger.info("Scrape job %s started in background thread", job_id)

        return result

    def get_active_job(self) -> Optional[dict]:
        """Return the currently running/queued job, or None."""
        Session, engine = _make_session_factory()
        session = Session()
        try:
            job = (
                session.query(ScrapeJob)
                .filter(ScrapeJob.status.in_(["queued", "running"]))
                .first()
            )
            return job.serialize() if job else None
        finally:
            Session.remove()
            engine.dispose()

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Return status of a specific job, or None if not found."""
        Session, engine = _make_session_factory()
        session = Session()
        try:
            job = session.query(ScrapeJob).filter_by(job_id=job_id).first()
            return job.serialize() if job else None
        finally:
            Session.remove()
            engine.dispose()

    def cancel_job(self, job_id: str) -> bool:
        """
        Request cancellation of a running job.

        Returns True if the job was found and cancel was requested.
        """
        Session, engine = _make_session_factory()
        session = Session()
        try:
            job = (
                session.query(ScrapeJob)
                .filter_by(job_id=job_id)
                .filter(ScrapeJob.status.in_(["queued", "running"]))
                .first()
            )
            if job is None:
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now()
            session.commit()
        finally:
            Session.remove()
            engine.dispose()

        # Signal the thread to stop
        cancel_event = self._cancel_events.get(job_id)
        if cancel_event:
            cancel_event.set()

        logger.info("Scrape job %s cancel requested", job_id)
        return True

    def get_job_history(self, limit: int = 20) -> List[dict]:
        """Return recent scrape jobs ordered by start time descending."""
        Session, engine = _make_session_factory()
        session = Session()
        try:
            jobs = (
                session.query(ScrapeJob)
                .order_by(desc(ScrapeJob.started_at))
                .limit(limit)
                .all()
            )
            return [j.serialize() for j in jobs]
        finally:
            Session.remove()
            engine.dispose()

    def get_db_stats(self) -> dict:
        """Return offer counts per brand and totals."""
        Session, engine = _make_session_factory()
        session = Session()
        try:
            total = session.query(func.count(Offer.id)).scalar() or 0

            brand_counts = (
                session.query(Brand.name, func.count(Offer.id))
                .join(Model, Brand.id == Model.brand_id)
                .join(Offer, Model.id == Offer.model_id)
                .group_by(Brand.name)
                .order_by(func.count(Offer.id).desc())
                .all()
            )

            latest_scrape = session.query(func.max(Offer.scraped_at)).scalar()

            # Build lookup of counts per brand
            count_map = {name: count for name, count in brand_counts}

            return {
                "total_offers": total,
                "available_brands": sorted(CAR_BRANDS),
                "brands": [
                    {"name": name, "count": count}
                    for name, count in brand_counts
                ],
                "latest_scrape": latest_scrape.isoformat() if latest_scrape else None,
            }
        finally:
            Session.remove()
            engine.dispose()

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _run_in_thread(
        self,
        job_id: str,
        brands: Optional[List[str]],
        cancel_event: threading.Event,
    ) -> None:
        """Run the pipeline in a background thread with its own event loop."""
        Session, engine = _make_session_factory()

        def update_status(**kwargs) -> None:
            """Write progress to the scrape_jobs row."""
            session = Session()
            try:
                job = session.query(ScrapeJob).filter_by(job_id=job_id).first()
                if job:
                    for k, v in kwargs.items():
                        setattr(job, k, v)
                    session.commit()
            except Exception as exc:
                logger.warning("Failed to update job %s status: %s", job_id, exc)
                session.rollback()
            finally:
                Session.remove()

        def progress_callback(stats: dict) -> None:
            """Called by PipelineRunner after each brand/chunk."""
            update_status(
                current_brand=stats.get("current_brand"),
                brands_done=json.dumps(stats.get("brands_done", [])),
                processed_urls=stats.get("processed_urls", 0),
                saved_count=stats.get("saved", 0),
                failed_count=stats.get("failed", 0),
                filtered_count=stats.get("filtered", 0),
            )

        try:
            update_status(status="running")

            from pipeline.runner import PipelineRunner

            runner = PipelineRunner(
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
            asyncio.run(runner.run(brands=brands))

            # Final stats
            update_status(
                status="completed",
                completed_at=datetime.now(),
                saved_count=runner._runtime_stats["saved"],
                failed_count=runner._runtime_stats["failed"],
                filtered_count=runner._runtime_stats["filtered"],
                processed_urls=sum(runner._runtime_stats.values()),
            )
            logger.info("Scrape job %s completed", job_id)

        except Exception as exc:
            error_msg = str(exc)[:1000]
            logger.error("Scrape job %s failed: %s", job_id, error_msg)
            update_status(
                status="failed",
                completed_at=datetime.now(),
                error_message=error_msg,
            )
        finally:
            self._cancel_events.pop(job_id, None)
            engine.dispose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cleanup_stale_jobs(self, session) -> None:
        """Mark running jobs from dead workers as failed."""
        stale = (
            session.query(ScrapeJob)
            .filter(ScrapeJob.status.in_(["queued", "running"]))
            .all()
        )
        for job in stale:
            if job.worker_pid and not _is_pid_alive(job.worker_pid):
                logger.warning(
                    "Cleaning stale job %s (worker PID %s is dead)",
                    job.job_id,
                    job.worker_pid,
                )
                job.status = "failed"
                job.completed_at = datetime.now()
                job.error_message = f"Worker PID {job.worker_pid} died"
        session.commit()
