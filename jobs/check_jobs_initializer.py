from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.config import (
    APSCHEDULER_MISFIRE_GRACE_SECONDS,
    CHECK_FOR_JOBS_INTERVAL_SECONDS,
)
from scheduler.jobs.periodic.periodic_checker_job import check_and_execute_ready_jobs


async def initialize_jobs_checker(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        check_and_execute_ready_jobs,
        trigger=IntervalTrigger(seconds=CHECK_FOR_JOBS_INTERVAL_SECONDS),
        id="check_pending_jobs",
        name="Check Pending Jobs",
        replace_existing=True,
        misfire_grace_time=APSCHEDULER_MISFIRE_GRACE_SECONDS,
    )
