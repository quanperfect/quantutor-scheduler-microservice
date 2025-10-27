import asyncio
from uuid import UUID
from typing import Optional, Dict, Any

from rabbitmq.rabbitmq_controller import rabbitmq_controller
from schemas.rabbitmq_events import JobExecuteEvent, JobEventTypeEnum
from scheduler.models.job import Job, JobStatusEnum
from scheduler.repositories.job_repository import JobRepository
from scheduler.database.postgres_database import get_db_context
from utils.timezone_utils import now_utc
from custom_logging.custom_logger import get_logger

clogger = get_logger()
MODULE_NAME = "JOB_EXECUTOR"


class JobExecutor:
    @staticmethod
    async def execute_job(job: Job) -> bool:
        try:
            async with get_db_context() as session:
                job_repo = JobRepository(session)
                await job_repo.mark_sent(job.job_id)

            event = JobExecuteEvent(
                event_type=JobEventTypeEnum.JOB_EXECUTE,
                job_id=job.job_id,
                job_type=job.job_type.value,
                scheduled_for=job.scheduled_for,
                sent_at=now_utc(),
                timeout_seconds=job.timeout_seconds,
                metadata=job.job_metadata or {},
            )

            success = await rabbitmq_controller.publish(
                routing_key=f"jobs.execute.{job.job_type.value}",
                message=event.model_dump(mode="json"),
                persistent=True,
            )

            if success:
                clogger.info(
                    f"[{MODULE_NAME}] Job {job.job_id} ({job.job_type.value}) "
                    f"published to RabbitMQ"
                )

                asyncio.create_task(
                    JobExecutor._monitor_job_timeout(job.job_id, job.timeout_seconds)
                )

                return True
            else:
                clogger.error(
                    f"[{MODULE_NAME}] Failed to publish job {job.job_id} to RabbitMQ"
                )
                return False

        except Exception as e:
            clogger.error(
                f"[{MODULE_NAME}] Error executing job {job.job_id}: {e}", exc_info=True
            )
            return False

    @staticmethod
    async def _monitor_job_timeout(job_id: UUID, timeout_seconds: int) -> None:
        await asyncio.sleep(timeout_seconds)

        try:
            async with get_db_context() as session:
                job_repo = JobRepository(session)
                job = await job_repo.get_by_id(job_id)

                if job and job.status == JobStatusEnum.SENT:
                    await job_repo.mark_timeout(job_id)
                    clogger.warning(
                        f"[{MODULE_NAME}] Job {job_id} timed out after "
                        f"{timeout_seconds} seconds"
                    )

                    if job.is_retriable():
                        clogger.info(
                            f"[{MODULE_NAME}] Job {job_id} will be retried later by retrier logic"
                            f"(attempt {job.attempts_count}/{job.max_attempts})"
                        )
        except Exception as e:
            clogger.error(
                f"[{MODULE_NAME}] Error monitoring timeout for job {job_id}: {e}",
                exc_info=True,
            )
