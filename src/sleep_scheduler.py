#!/usr/bin/env python3
"""
Sleep-Time Compute Scheduler for HippoGraph Pro.

Two trigger mechanisms:
  1. Time-based: run every SLEEP_INTERVAL_HOURS (default: 6h)
  2. Threshold-based: run after SLEEP_NOTE_THRESHOLD new notes added (default: 50)

Runs as a background daemon thread. Call start_scheduler() from server.py.
Call notify_note_added() from add_note endpoint to update counter.
"""
import os
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Config from environment
SLEEP_INTERVAL_HOURS = float(os.getenv("SLEEP_INTERVAL_HOURS", "6"))
SLEEP_NOTE_THRESHOLD = int(os.getenv("SLEEP_NOTE_THRESHOLD", "50"))
DB_PATH = os.getenv("DB_PATH", "/app/data/memory.db")

# State
_notes_since_last_sleep = 0
_last_sleep_time = None
_scheduler_thread = None
_lock = threading.Lock()
_running = False


def _run_sleep_compute():
    """Execute sleep_compute in a separate thread (non-blocking)."""
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))

    def _worker():
        try:
            logger.info("🌙 Sleep-Time Compute triggered")
            import sleep_compute
            result = sleep_compute.run_all(DB_PATH)
            logger.info(f"🌙 Sleep-Time Compute complete: {result}")
        except Exception as e:
            logger.error(f"🌙 Sleep-Time Compute error: {e}", exc_info=True)

    t = threading.Thread(target=_worker, daemon=True, name="sleep-compute-worker")
    t.start()


def notify_note_added():
    """Call this every time a note is successfully added."""
    global _notes_since_last_sleep

    if SLEEP_NOTE_THRESHOLD <= 0:
        return  # threshold trigger disabled

    with _lock:
        _notes_since_last_sleep += 1
        count = _notes_since_last_sleep

    if count >= SLEEP_NOTE_THRESHOLD:
        with _lock:
            # Double-check under lock to avoid race
            if _notes_since_last_sleep >= SLEEP_NOTE_THRESHOLD:
                _notes_since_last_sleep = 0
                logger.info(
                    f"🌙 Note threshold reached ({SLEEP_NOTE_THRESHOLD}), "
                    f"triggering sleep_compute"
                )
        _run_sleep_compute()


def _time_based_loop():
    """Background loop: sleep every SLEEP_INTERVAL_HOURS hours."""
    global _last_sleep_time, _running

    interval_sec = SLEEP_INTERVAL_HOURS * 3600
    logger.info(
        f"🌙 Sleep scheduler started "
        f"(interval={SLEEP_INTERVAL_HOURS}h, "
        f"note_threshold={SLEEP_NOTE_THRESHOLD})"
    )

    while _running:
        # Sleep in small increments for clean shutdown
        for _ in range(int(interval_sec / 10)):
            if not _running:
                return
            time.sleep(10)

        if _running:
            _last_sleep_time = datetime.now()
            _run_sleep_compute()


def start_scheduler():
    """Start the background scheduler. Call once from server startup."""
    global _scheduler_thread, _running

    if SLEEP_INTERVAL_HOURS <= 0:
        logger.info("🌙 Sleep scheduler disabled (SLEEP_INTERVAL_HOURS=0)")
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.warning("🌙 Scheduler already running")
        return

    _running = True
    _scheduler_thread = threading.Thread(
        target=_time_based_loop,
        daemon=True,
        name="sleep-scheduler"
    )
    _scheduler_thread.start()
    logger.info("🌙 Sleep scheduler thread started")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global _running
    _running = False
    logger.info("🌙 Sleep scheduler stopped")


def get_status():
    """Return scheduler status dict (for /health or /stats endpoint)."""
    return {
        "interval_hours": SLEEP_INTERVAL_HOURS,
        "note_threshold": SLEEP_NOTE_THRESHOLD,
        "notes_since_last_sleep": _notes_since_last_sleep,
        "last_sleep_time": _last_sleep_time.isoformat() if _last_sleep_time else None,
        "scheduler_running": _scheduler_thread.is_alive() if _scheduler_thread else False,
    }
