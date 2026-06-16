"""Background scheduler for periodic product checks."""

import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from . import database as db
from .engine import check_product

logger = logging.getLogger("marketeye.scheduler")

_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _dispatch_loop,
        IntervalTrigger(seconds=30),
        id="_marketeye_dispatch",
        name="MarketEye dispatch",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (checking every 30s)")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _dispatch_loop():
    """Check all enabled products that are due."""
    products = db.get_products()
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    for p in products:
        if not p["enabled"]:
            continue
        last = db.get_latest_snapshot(p["id"])
        if last:
            last_time = __import__("datetime").datetime.fromisoformat(last["fetched_at"])
            elapsed = (now - last_time).total_seconds() / 60
            if elapsed < p["check_interval_minutes"]:
                continue

        logger.info(f"Checking: {p['name']}")
        try:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(check_product(p["id"]))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Check failed [{p['name']}]: {e}")
