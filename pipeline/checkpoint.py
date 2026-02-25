"""
Pipeline Checkpoint Manager
============================

Tracks scraping progress so the pipeline can resume after crashes.
Each run gets a unique session ID and its own checkpoint file.

Problem solved:
    Scraping 3000 Škoda listings → crash at 2400 → restart from 2400, not 0.

Storage:
    pipeline_checkpoints/{session_id}.json

Structure:
    {
        "session_id": "20250225_143000",
        "started_at": "2025-02-25T14:30:00",
        "last_updated": "2025-02-25T15:45:00",
        "status": "in_progress",
        "brands_done": ["audi", "bmw"],
        "processed_urls": {
            "https://auto.bazos.cz/inzerat/123/": "saved",
            "https://auto.bazos.cz/inzerat/456/": "failed",
            "https://auto.bazos.cz/inzerat/789/": "filtered"
        },
        "stats": {
            "total_processed": 2400,
            "saved": 2210,
            "failed": 95,
            "filtered": 85,
            "skipped": 10
        }
    }

Usage:
    # New session
    cp = CheckpointManager()

    # Resume last incomplete
    cp = CheckpointManager.resume_last()

    # Resume specific session
    cp = CheckpointManager(session_id="20250225_143000")
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

CHECKPOINTS_DIR = Path("pipeline_checkpoints")

# How often to flush checkpoint to disk (every N processed URLs)
SAVE_EVERY = 25

# URL statuses
STATUS_SAVED = "saved"
STATUS_FILTERED = "filtered"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

# Statuses that count as "done" (won't be re-processed on resume)
DONE_STATUSES = {STATUS_SAVED, STATUS_FILTERED}


class CheckpointManager:
    """
    Tracks pipeline progress with automatic save/resume.

    Thread-safe: saves are atomic (write to temp file, rename).
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Args:
            session_id: Resume existing session, or None to start fresh.
        """
        CHECKPOINTS_DIR.mkdir(exist_ok=True)

        if session_id:
            self.session_id = session_id
            self.checkpoint_file = CHECKPOINTS_DIR / f"{session_id}.json"
            self.data = self._load_existing()
        else:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.checkpoint_file = CHECKPOINTS_DIR / f"{self.session_id}.json"
            self.data = self._new_data()

        # Unsaved counter - save every SAVE_EVERY marks
        self._unsaved_count = 0

        logger.info(
            f"Checkpoint session: {self.session_id} | "
            f"Status: {self.data['status']} | "
            f"Already saved: {self.data['stats']['saved']} | "
            f"Brands done: {self.data['brands_done']}"
        )

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def is_url_done(self, url: str) -> bool:
        """
        Check if URL was already successfully processed.
        Returns True for 'saved' and 'filtered' (but NOT 'failed').
        Failed URLs will be retried on resume.
        """
        status = self.data["processed_urls"].get(url)
        return status in DONE_STATUSES

    def mark_url_done(self, url: str, status: str = STATUS_SAVED):
        """
        Record URL outcome. Automatically saves to disk every SAVE_EVERY calls.

        Args:
            url: The processed URL
            status: 'saved' | 'filtered' | 'failed'
        """
        prev = self.data["processed_urls"].get(url)
        self.data["processed_urls"][url] = status

        # Update stats (only count new entries, not overwrites)
        if prev is None:
            self.data["stats"]["total_processed"] += 1
            if status in self.data["stats"]:
                self.data["stats"][status] += 1

        # Periodic save
        self._unsaved_count += 1
        if self._unsaved_count >= SAVE_EVERY:
            self.save()
            self._unsaved_count = 0

    def mark_brand_done(self, brand: str):
        """Mark an entire brand as completed (all pages processed)."""
        if brand not in self.data["brands_done"]:
            self.data["brands_done"].append(brand)
        self.save(force=True)
        logger.info(f"Checkpoint: brand '{brand}' marked as complete.")

    def is_brand_done(self, brand: str) -> bool:
        """Check if brand was fully processed in this session."""
        return brand in self.data["brands_done"]

    def save(self, force: bool = False):
        """
        Persist checkpoint to disk.
        Uses atomic write (temp file + rename) to prevent corruption on crash.
        """
        self.data["last_updated"] = datetime.now().isoformat()
        tmp_file = self.checkpoint_file.with_suffix(".tmp")
        try:
            tmp_file.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            tmp_file.rename(self.checkpoint_file)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def complete(self):
        """Mark session as fully completed."""
        self.data["status"] = "completed"
        self.data["completed_at"] = datetime.now().isoformat()
        self.save(force=True)
        stats = self.data["stats"]
        logger.info(
            f"Session {self.session_id} completed: "
            f"saved={stats['saved']}, failed={stats['failed']}, "
            f"filtered={stats['filtered']}"
        )

    def get_stats(self) -> dict:
        """Return current statistics."""
        return self.data["stats"].copy()

    def get_failed_urls(self) -> List[str]:
        """Return list of URLs that failed (for retry or inspection)."""
        return [
            url for url, status in self.data["processed_urls"].items()
            if status == STATUS_FAILED
        ]

    # ------------------------------------------------------------------
    # Class methods for session management
    # ------------------------------------------------------------------

    @classmethod
    def resume_last(cls) -> Optional['CheckpointManager']:
        """
        Resume the most recent incomplete session.
        Returns None if no incomplete session found (caller should create new one).
        """
        session_id = cls._get_latest_incomplete_id()
        if session_id:
            logger.info(f"Auto-resuming session: {session_id}")
            return cls(session_id=session_id)
        return None

    @classmethod
    def list_sessions(cls) -> List[dict]:
        """List all checkpoint sessions, newest first."""
        if not CHECKPOINTS_DIR.exists():
            return []

        sessions = []
        for f in sorted(CHECKPOINTS_DIR.glob("*.json"), reverse=True):
            if f.suffix == ".json" and not f.stem.endswith(".tmp"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    sessions.append({
                        "session_id": data.get("session_id"),
                        "started_at": data.get("started_at"),
                        "last_updated": data.get("last_updated"),
                        "status": data.get("status"),
                        "stats": data.get("stats", {}),
                        "brands_done": data.get("brands_done", []),
                    })
                except Exception:
                    pass
        return sessions

    @classmethod
    def print_sessions(cls):
        """Pretty-print all sessions for CLI."""
        sessions = cls.list_sessions()
        if not sessions:
            print("No checkpoint sessions found.")
            return

        print(f"\n{'SESSION ID':<22} {'STATUS':<12} {'SAVED':>7} {'FAILED':>7} {'BRANDS DONE'}")
        print("-" * 70)
        for s in sessions:
            stats = s.get("stats", {})
            print(
                f"{s['session_id']:<22} "
                f"{s['status']:<12} "
                f"{stats.get('saved', 0):>7} "
                f"{stats.get('failed', 0):>7} "
                f"  {', '.join(s['brands_done']) or '-'}"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _new_data(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "in_progress",
            "brands_done": [],
            "processed_urls": {},
            "stats": {
                "total_processed": 0,
                "saved": 0,
                "failed": 0,
                "filtered": 0,
                "skipped": 0,
            }
        }

    def _load_existing(self) -> dict:
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
                # Ensure all expected keys exist (forward-compatibility)
                data.setdefault("brands_done", [])
                data.setdefault("processed_urls", {})
                data.setdefault("stats", {})
                for k in ("total_processed", "saved", "failed", "filtered", "skipped"):
                    data["stats"].setdefault(k, 0)
                return data
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Corrupt checkpoint {self.checkpoint_file}: {e}. Starting fresh.")

        logger.info(f"No existing checkpoint for session {self.session_id}, starting fresh.")
        return self._new_data()

    @classmethod
    def _get_latest_incomplete_id(cls) -> Optional[str]:
        for session in cls.list_sessions():
            if session["status"] == "in_progress":
                return session["session_id"]
        return None
