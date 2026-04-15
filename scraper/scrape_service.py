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
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, scoped_session

from database.model import Base, ScrapeJob, Brand, Model, Offer
from scraper.data_scrap import CAR_BRANDS
from webapp.config import get_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared engine (one per worker process, reused across all API calls)
# ---------------------------------------------------------------------------

_config = get_config()
_engine = create_engine(
    _config.DATABASE_URI,
    pool_pre_ping=True,
    pool_recycle=3600,
)
_ScopedSession = scoped_session(sessionmaker(bind=_engine))


@contextmanager
def _get_session():
    """Scoped session context manager for the shared engine."""
    session = _ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _ScopedSession.remove()


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
        with _get_session() as session:
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
            session.flush()
            result = job.serialize()

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
        with _get_session() as session:
            job = (
                session.query(ScrapeJob)
                .filter(ScrapeJob.status.in_(["queued", "running"]))
                .first()
            )
            return job.serialize() if job else None

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Return status of a specific job, or None if not found."""
        with _get_session() as session:
            job = session.query(ScrapeJob).filter_by(job_id=job_id).first()
            return job.serialize() if job else None

    def cancel_job(self, job_id: str) -> bool:
        """
        Request cancellation of a running job.

        Returns True if the job was found and cancel was requested.
        """
        with _get_session() as session:
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

        # Signal the thread to stop
        cancel_event = self._cancel_events.get(job_id)
        if cancel_event:
            cancel_event.set()

        logger.info("Scrape job %s cancel requested", job_id)
        return True

    def get_job_history(self, limit: int = 20) -> List[dict]:
        """Return recent scrape jobs ordered by start time descending."""
        with _get_session() as session:
            jobs = (
                session.query(ScrapeJob)
                .order_by(desc(ScrapeJob.started_at))
                .limit(limit)
                .all()
            )
            return [j.serialize() for j in jobs]

    def get_db_stats(self) -> dict:
        """Return offer counts per brand and totals."""
        with _get_session() as session:
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

            return {
                "total_offers": total,
                "available_brands": sorted(CAR_BRANDS),
                "brands": [
                    {"name": name, "count": count}
                    for name, count in brand_counts
                ],
                "latest_scrape": latest_scrape.isoformat() if latest_scrape else None,
            }

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _run_in_thread(
        self,
        job_id: str,
        brands: Optional[List[str]],
        cancel_event: threading.Event,
    ) -> None:
        """Run the pipeline in a background thread with its own event loop.

        Uses a dedicated engine so the background thread does not share
        connections with the Flask request threads.
        """
        bg_engine = create_engine(
            _config.DATABASE_URI,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        BgSession = scoped_session(sessionmaker(bind=bg_engine))

        def update_status(**kwargs) -> None:
            """Write progress to the scrape_jobs row."""
            session = BgSession()
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
                BgSession.remove()

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
            bg_engine.dispose()

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
