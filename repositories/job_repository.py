from typing import Any, Dict, Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler.models.job import Job, JobStatusEnum, JobTypeEnum
from utils.timezone_utils import now_utc

from sqlalchemy import or_, and_


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID) -> Optional[Job]:
        result = await self.session.execute(select(Job).where(Job.job_id == job_id))
        return result.scalar_one_or_none()

    async def get_jobs_ready_for_execution(self, limit: int = 100) -> List[Job]:
        now = now_utc()

        result = await self.session.execute(
            select(Job)
            .where(
                or_(
                    and_(Job.status == JobStatusEnum.PENDING, Job.scheduled_for <= now),
                    and_(
                        Job.status == JobStatusEnum.FAILED,
                        Job.attempts_count < Job.max_attempts,
                        Job.updated_at
                        + Job.min_retry_delay_seconds * timedelta(seconds=1)
                        <= now,
                    ),
                    and_(
                        Job.status == JobStatusEnum.TIMEOUT,
                        Job.attempts_count < Job.max_attempts,
                        Job.updated_at
                        + Job.min_retry_delay_seconds * timedelta(seconds=1)
                        <= now,
                    ),
                )
            )
            .order_by(Job.scheduled_for)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_sent_jobs_pending_response(self) -> List[Job]:
        result = await self.session.execute(
            select(Job).where(Job.status == JobStatusEnum.SENT)
        )
        return list(result.scalars().all())

    async def get_recent_jobs(self, limit: int = 20) -> List[Job]:
        result = await self.session.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def update_job(self, job: Job) -> Job:
        await self.session.merge(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def mark_sent(self, job_id: UUID) -> Optional[Job]:
        """Mark job as sent"""
        job = await self.get_by_id(job_id)
        if job:
            job.mark_sent()
            await self.update_job(job)
        return job

    async def mark_completed(
        self,
        job_id: UUID,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> Optional[Job]:
        job = await self.get_by_id(job_id)
        if job:
            job.mark_completed(result=result, duration_ms=duration_ms)
            await self.update_job(job)
        return job

    async def mark_failed(self, job_id: UUID, error_message: str) -> Optional[Job]:
        job = await self.get_by_id(job_id)
        if job:
            job.mark_failed(error_message)
            await self.update_job(job)
        return job

    async def mark_timeout(self, job_id: UUID) -> Optional[Job]:
        job = await self.get_by_id(job_id)
        if job:
            job.mark_timeout()
            await self.update_job(job)
        return job
