"""Cron-style scheduling of listing checks based on the configured check times."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import TIMEZONE
from app.models import Settings
from app.monitor import run_check

logger = logging.getLogger(__name__)

JOB_ID_PREFIX = "listing-check-"

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def apply_schedule(settings: Settings) -> None:
    """Replace the scheduled check jobs with the ones described by ``settings``."""
    for job in scheduler.get_jobs():
        if job.id.startswith(JOB_ID_PREFIX):
            job.remove()
    if not settings.enabled:
        logger.info("Monitor disabled; no checks scheduled")
        return
    for check_time in settings.check_time_list:
        hour, minute = check_time.split(":")
        scheduler.add_job(
            run_check,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=TIMEZONE),
            id=f"{JOB_ID_PREFIX}{check_time}",
            misfire_grace_time=3600,
            coalesce=True,
        )
    logger.info("Checks scheduled at %s", ", ".join(settings.check_time_list))
