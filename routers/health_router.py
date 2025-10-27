from typing import Any, Dict
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "job_scheduler",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# @router.get("/scheduler")
# async def scheduler_health() -> Dict[str, Any]:
#     from scheduler.main import scheduler

#     if not scheduler:
#         return {
#             "status": "not_initialized",
#             "running": False,
#             "jobs": []
#         }

#     return {
#         "status": "running" if scheduler.running else "stopped",
#         "running": scheduler.running,
#         "jobs": [
#             {
#                 "id": job.id,
#                 "name": job.name,
#                 "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
#                 "trigger": str(job.trigger)
#             }
#             for job in scheduler.get_jobs()
#         ]
#     }
