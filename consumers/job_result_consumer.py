from typing import Dict, Any

from rabbitmq.rabbitmq_controller import rabbitmq_controller
from schemas.rabbitmq_events import (
    JobEvent,
    parse_job_event,
    JobCompletedEvent,
    JobFailedEvent,
)
from scheduler.repositories.job_repository import JobRepository
from scheduler.database.postgres_database import get_db_context
from scheduler.config import RABBITMQ_QUEUE_NAME
from custom_logging.custom_logger import get_logger

clogger = get_logger()
MODULE_NAME = "JOB_RESULT_CONSUMER"


async def process_job_result_event(event_dict: Dict[str, Any]) -> None:
    try:
        clogger.debug(
            f"[{MODULE_NAME}] Processing job result event, data:  {event_dict}"
        )
        event = parse_job_event(event_dict)

        if isinstance(event, JobCompletedEvent):
            await _process_successful_job(event)
        elif isinstance(event, JobFailedEvent):
            await _process_failed_job(event)
        else:
            clogger.error(f"[{MODULE_NAME}] Unknown job event passed for processing")
    except ValueError as e:
        clogger.error(f"[{MODULE_NAME}] Failed to parse job event: {e}", exc_info=True)
    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Error processing job result event: {e}", exc_info=True
        )


async def _process_successful_job(job_event: JobCompletedEvent):
    async with get_db_context() as session:
        job_repo = JobRepository(session)
        await job_repo.mark_completed(
            job_id=job_event.job_id,
            result=job_event.result,
            duration_ms=job_event.execution_duration_ms,
        )
        clogger.info(f"[{MODULE_NAME}] Job {job_event.job_id} completed successfully")


async def _process_failed_job(job_event: JobFailedEvent):
    async with get_db_context() as session:
        job_repo = JobRepository(session)
        err_msg = job_event.error_message if job_event.error_message else "unknown"
        await job_repo.mark_failed(job_id=job_event.job_id, error_message=err_msg)
        clogger.warning(
            f"[{MODULE_NAME}] Job {job_event.job_id} failed: {job_event.error_message}"
        )


async def start_job_result_consumer() -> None:
    try:
        await rabbitmq_controller.consume(
            queue_name=RABBITMQ_QUEUE_NAME,
            routing_keys=["jobs.completed", "jobs.failed"],
            callback=process_job_result_event,
            auto_ack=False,
        )
        clogger.info(
            f"[{MODULE_NAME}] Started consuming job results from RabbitMQ "
            f"(queue: {RABBITMQ_QUEUE_NAME})"
        )
    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Failed to start job result consumer: {e}", exc_info=True
        )
        raise
