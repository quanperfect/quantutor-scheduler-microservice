from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from utils.timezone_utils import now_utc


class NotificationUserRoleEnum(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"


class NotificationEventTypeEnum(str, Enum):
    ERROR_CAUGHT = "error.error_caught"
    MFA_CODE = "auth.mfa_code"
    PASSWORD_RESET_CODE = "auth.password_reset_code"
    PASSWORD_RESET_NOTIFICATION = "auth.password_reset_notification"
    LOGIN_NOTIFICATION = "auth.login_notification"


class JobEventTypeEnum(str, Enum):
    """Job scheduler event types"""
    JOB_EXECUTE = "jobs.execute"
    JOB_COMPLETED = "jobs.completed"
    JOB_FAILED = "jobs.failed"


class UserNotificationEventBase(BaseModel):
    """Notifications for users"""

    event_type: str
    notification_id: UUID
    user_id: UUID
    telegram_user_id: str
    user_first_name: str
    user_last_name: str
    user_role: NotificationUserRoleEnum
    timestamp: datetime = now_utc()

    @field_validator("timestamp")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


# auth notification events - aligned with email_utils.py templates


class MfaCodeData(BaseModel):
    code: str
    code_expires_at: datetime
    client_ip: Optional[str] = None
    client_location: Optional[str] = None
    client_fingerprint: Optional[str] = None

    @field_validator("code_expires_at")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


class MfaCodeEvent(UserNotificationEventBase):
    event_type: Literal[NotificationEventTypeEnum.MFA_CODE] = (
        NotificationEventTypeEnum.MFA_CODE
    )
    data: MfaCodeData


class PasswordResetCodeData(BaseModel):
    code: str
    code_expires_at: datetime
    client_ip: Optional[str] = None
    client_location: Optional[str] = None
    client_fingerprint: Optional[str] = None

    @field_validator("code_expires_at")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


class PasswordResetCodeEvent(UserNotificationEventBase):
    event_type: Literal[NotificationEventTypeEnum.PASSWORD_RESET_CODE] = (
        NotificationEventTypeEnum.PASSWORD_RESET_CODE
    )
    data: PasswordResetCodeData


class PasswordResetNotificationData(BaseModel):
    client_ip: Optional[str] = None
    client_location: Optional[str] = None
    client_fingerprint: Optional[str] = None


class PasswordResetNotificationEvent(UserNotificationEventBase):
    event_type: Literal[NotificationEventTypeEnum.PASSWORD_RESET_NOTIFICATION] = (
        NotificationEventTypeEnum.PASSWORD_RESET_NOTIFICATION
    )
    data: PasswordResetNotificationData


class LoginNotificationData(BaseModel):
    login_time: datetime
    client_ip: Optional[str] = None
    client_location: Optional[str] = None
    client_fingerprint: Optional[str] = None

    @field_validator("login_time")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


class LoginNotificationEvent(UserNotificationEventBase):
    event_type: Literal[NotificationEventTypeEnum.LOGIN_NOTIFICATION] = (
        NotificationEventTypeEnum.LOGIN_NOTIFICATION
    )
    data: LoginNotificationData


# type union for all auth events
AuthNotificationEvent = Union[
    MfaCodeEvent,
    PasswordResetCodeEvent,
    PasswordResetNotificationEvent,
    LoginNotificationEvent,
]


class ServerErrorData(BaseModel):
    exception_type: Optional[str]
    exception_message: Optional[str]

    # for external api
    request_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    client_ip: Optional[str] = None
    client_location: Optional[str] = None
    client_fingerprint: Optional[str] = None

    # for internal errors (no api)
    correlation_id: Optional[str] = None
    source: Optional[str] = None

    occurred_at: datetime = now_utc()

    @field_validator("occurred_at")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


class ServerNotificationEvent(BaseModel):
    """Error monitoring of main FastAPI backend for admin"""

    event_type: Literal[NotificationEventTypeEnum.ERROR_CAUGHT] = (
        NotificationEventTypeEnum.ERROR_CAUGHT
    )
    error_data: ServerErrorData
    timestamp: datetime = now_utc()

    @field_validator("timestamp")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


# ================================
# Job Scheduler Events
# ================================


class JobExecuteEvent(BaseModel):
    """Job execution request (Scheduler → FastAPI)"""

    event_type: Literal[JobEventTypeEnum.JOB_EXECUTE] = JobEventTypeEnum.JOB_EXECUTE
    job_id: UUID
    job_type: str  # JobTypeEnum value from job_scheduler
    scheduled_for: datetime
    sent_at: datetime
    timeout_seconds: int = 300
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("scheduled_for", "sent_at")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


class JobCompletedEvent(BaseModel):
    """Job completion response (FastAPI → Scheduler)"""

    event_type: Literal[JobEventTypeEnum.JOB_COMPLETED] = (
        JobEventTypeEnum.JOB_COMPLETED
    )
    job_id: UUID
    completed_at: datetime
    execution_duration_ms: Optional[int] = None
    result: Optional[Dict[str, Any]] = None

    @field_validator("completed_at")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


class JobFailedEvent(BaseModel):
    """Job failure response (FastAPI → Scheduler)"""

    event_type: Literal[JobEventTypeEnum.JOB_FAILED] = JobEventTypeEnum.JOB_FAILED
    job_id: UUID
    failed_at: datetime
    error_message: str
    should_retry: bool = True

    @field_validator("failed_at")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v.astimezone(timezone.utc)


# Type unions
JobEvent = Union[JobExecuteEvent, JobCompletedEvent, JobFailedEvent]


def parse_event(
    event_dict: Dict[str, Any],
) -> Union[AuthNotificationEvent, ServerNotificationEvent]:
    event_type = event_dict.get("event_type")

    event_map = {
        # user notifications
        NotificationEventTypeEnum.MFA_CODE.value: MfaCodeEvent,
        NotificationEventTypeEnum.PASSWORD_RESET_CODE.value: PasswordResetCodeEvent,
        NotificationEventTypeEnum.PASSWORD_RESET_NOTIFICATION.value: PasswordResetNotificationEvent,
        NotificationEventTypeEnum.LOGIN_NOTIFICATION.value: LoginNotificationEvent,
        # system notification for admin
        NotificationEventTypeEnum.ERROR_CAUGHT.value: ServerNotificationEvent,
    }

    event_class = event_map.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown event type: {event_type}")

    return event_class(**event_dict)


def parse_job_event(event_dict: Dict[str, Any]) -> JobEvent:
    """Parse job-related events"""
    event_type = event_dict.get("event_type")

    event_map = {
        JobEventTypeEnum.JOB_EXECUTE.value: JobExecuteEvent,
        JobEventTypeEnum.JOB_COMPLETED.value: JobCompletedEvent,
        JobEventTypeEnum.JOB_FAILED.value: JobFailedEvent,
    }

    event_class = event_map.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown job event type: {event_type}")

    return event_class(**event_dict)
