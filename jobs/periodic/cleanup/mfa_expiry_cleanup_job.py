from scheduler.config import (
    CLEANUP_JOB_MAX_RETRIES,
    CLEANUP_JOB_MIN_RETRY_DELAY_SECONDS,
    CLEANUP_JOB_TIMEOUT_SECONDS,
)
from scheduler.database.postgres_database import get_db_context
from scheduler.models.job import Job, JobTypeEnum
from scheduler.repositories.job_repository import JobRepository
from scheduler.jobs.job_executor import JobExecutor
from utils.timezone_utils import now_utc
from custom_logging.custom_logger import get_logger

clogger = get_logger()
MODULE_NAME = "MFA_EXPIRY_CLEANUP_JOB"


async def run_mfa_expiry_cleanup() -> None:
    try:
        clogger.info(f"[{MODULE_NAME}] Starting job")

        async with get_db_context() as session:
            job_repo = JobRepository(session)

            job = Job(
                job_type=JobTypeEnum.MFA_EXPIRY_CLEANUP,
                scheduled_for=now_utc(),
                timeout_seconds=CLEANUP_JOB_TIMEOUT_SECONDS,
                max_attempts=CLEANUP_JOB_MAX_RETRIES,
                min_retry_delay_seconds=CLEANUP_JOB_MIN_RETRY_DELAY_SECONDS,
                metadata={},
            )

            await job_repo.create(job)
            clogger.info(
                f"[{MODULE_NAME}] Created job: {job.job_id}"
            )

        await JobExecutor.execute_job(job)

    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Error in job: {e}", exc_info=True
        )

