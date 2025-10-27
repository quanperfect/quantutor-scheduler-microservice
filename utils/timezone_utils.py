from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None

    if dt.tzinfo is None:
        raise ValueError(
            "Datetime must be timezone-aware. Use timezone.utc for new datetimes."
        )

    return dt.astimezone(timezone.utc)


def validate_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError(
            "All datetimes must be timezone-aware. "
            "Use now_utc() or datetime.now(timezone.utc) for current time."
        )

    return dt.astimezone(timezone.utc)


def format_iso_utc(dt: datetime) -> str:
    utc_dt = ensure_utc(dt)
    return utc_dt.isoformat() if utc_dt else ""


UTC = timezone.utc
APP_TIMEZONE = UTC 
