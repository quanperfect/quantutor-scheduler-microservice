import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from rabbitmq.rabbitmq_controller import rabbitmq_controller
from scheduler.config import RABBITMQ_URL, VERSION
from scheduler.consumers.job_result_consumer import start_job_result_consumer
from scheduler.database.postgres_database import create_tables
from scheduler.jobs.check_jobs_initializer import initialize_jobs_checker
from scheduler.jobs.cleanup_jobs_initializer import initialize_cleanup_jobs
from scheduler.routers import health_router
from custom_logging.custom_logger import get_logger

clogger = get_logger()
MODULE_NAME = "JOB_SCHEDULER_MAIN"

scheduler: AsyncIOScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler

    clogger.info(f"[{MODULE_NAME}] Starting job scheduler microservice")

    try:
        await create_tables()
        clogger.info(f"[{MODULE_NAME}] Database tables created/verified")
    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Failed to create database tables: {e}", exc_info=True
        )
        raise

    try:
        await rabbitmq_controller.connect(RABBITMQ_URL)
        clogger.info(f"[{MODULE_NAME}] Connected to RabbitMQ")
    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Failed to connect to RabbitMQ: {e}", exc_info=True
        )
        raise

    try:
        consumer_task = asyncio.create_task(start_job_result_consumer())
        clogger.info(f"[{MODULE_NAME}] RabbitMQ consumer started")
    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Failed to start RabbitMQ consumer: {e}", exc_info=True
        )
        raise

    try:
        scheduler = AsyncIOScheduler(timezone="UTC")
        await initialize_cleanup_jobs(scheduler)
        await initialize_jobs_checker(scheduler)

        scheduler.start()
        clogger.info(
            f"[{MODULE_NAME}] APScheduler started with {len(scheduler.get_jobs())} jobs"
        )

        for job in scheduler.get_jobs():
            clogger.info(
                f"[{MODULE_NAME}] Scheduled job: {job.name} (ID: {job.id}) "
                f"- Next run: {job.next_run_time}"
            )

    except Exception as e:
        clogger.error(
            f"[{MODULE_NAME}] Failed to start APScheduler and initialize jobs: {e}", exc_info=True
        )
        raise

    clogger.info(f"[{MODULE_NAME}] Job scheduler microservice fully started")

    yield

    clogger.info(f"[{MODULE_NAME}] Shutting down job scheduler microservice")

    if scheduler and scheduler.running:
        scheduler.shutdown()
        clogger.info(f"[{MODULE_NAME}] APScheduler shut down")

    await rabbitmq_controller.disconnect()
    clogger.info(f"[{MODULE_NAME}] RabbitMQ disconnected")

    clogger.info(f"[{MODULE_NAME}] Shutdown complete")


app = FastAPI(
    title="Job Scheduler Microservice",
    description="Background job scheduling microservice for QuanTutor backend",
    version=VERSION,
    lifespan=lifespan,
)

app.include_router(health_router.router, prefix="/health", tags=["Health"])


@app.get("/")
async def root():
    return {"service": "job_scheduler", "version": VERSION, "status": "running"}
