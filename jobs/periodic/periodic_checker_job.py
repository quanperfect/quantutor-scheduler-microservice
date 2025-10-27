from scheduler.repositories.job_repository import JobRepository
from scheduler.database.postgres_database import get_db_context
from scheduler.jobs.job_executor import JobExecutor
from custom_logging.custom_logger import get_logger

clogger = get_logger()
MODULE_NAME = "PERIODIC_CHECKER_JOB"


async def check_and_execute_ready_jobs() -> None:
    try:
        async with get_db_context() as session:
            job_repo = JobRepository(session)

            pending_jobs = await job_repo.get_jobs_ready_for_execution(limit=3)

            if pending_jobs:
                clogger.info(
                    f"[{MODULE_NAME}] Found {len(pending_jobs)} (limit=3) pending jobs to execute"
                )

                for job in pending_jobs:
                    await JobExecutor.execute_job(job)

    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Error checking pending jobs: {e}", exc_info=True
        )
