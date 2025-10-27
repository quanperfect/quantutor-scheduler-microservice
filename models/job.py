import uuid
import enum
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    Enum as SAEnum,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from scheduler.database.postgres_database import Base
from utils.timezone_utils import now_utc


class JobTypeEnum(str, enum.Enum):
    MFA_EXPIRY_CLEANUP = "mfa_expiry_cleanup"
    FILE_CLEANUP = "file_cleanup"
    REGISTRATION_EXPIRY_CLEANUP = "registration_expiry_cleanup"
    RELATIONSHIP_CONSISTENCY_CHECK = "relationship_consistency_check"

    LESSON_REMINDER = "lesson_reminder"
    HOMEWORK_REMINDER = "homework_reminder"
    PAYMENT_REMINDER = "payment_reminder"
    TELEGRAM_LINK_REMINDER = "telegram_link_reminder"


class JobStatusEnum(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_type: Mapped[JobTypeEnum] = mapped_column(
        SAEnum(JobTypeEnum),
        nullable=False,
        index=True,
    )

    status: Mapped[JobStatusEnum] = mapped_column(
        SAEnum(JobStatusEnum),
        nullable=False,
        default=JobStatusEnum.PENDING,
        index=True,
    )

    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    attempts_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    min_retry_delay_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    job_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    execution_duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=now_utc,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Job(job_id={self.job_id}, type={self.job_type}, status={self.status})>"
        )

    def is_retriable(self) -> bool:
        return (
            self.status in [JobStatusEnum.FAILED, JobStatusEnum.TIMEOUT]
            and self.attempts_count < self.max_attempts
        )

    def mark_sent(self) -> None:
        self.status = JobStatusEnum.SENT
        self.sent_at = now_utc()
        self.attempts_count += 1

    def mark_completed(
        self, result: Optional[Dict[str, Any]] = None, duration_ms: Optional[int] = None
    ) -> None:
        self.status = JobStatusEnum.COMPLETED
        self.completed_at = now_utc()
        self.result = result
        self.execution_duration_ms = duration_ms

    def mark_failed(self, error_message: str) -> None:
        self.status = JobStatusEnum.FAILED
        self.error_message = error_message

    def mark_timeout(self) -> None:
        self.status = JobStatusEnum.TIMEOUT
