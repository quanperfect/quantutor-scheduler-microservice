from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.config import APSCHEDULER_MISFIRE_GRACE_SECONDS
from scheduler.jobs.periodic.cleanup.mfa_expiry_cleanup_job import (
    run_mfa_expiry_cleanup,
)


async def initialize_cleanup_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        run_mfa_expiry_cleanup,
        trigger=IntervalTrigger(minutes=1),
        id="mfa_expiry_cleanup",
        name="MFA Expiry Cleanup",
        replace_existing=True,
        misfire_grace_time=APSCHEDULER_MISFIRE_GRACE_SECONDS,
    )

    # todo other jobs
