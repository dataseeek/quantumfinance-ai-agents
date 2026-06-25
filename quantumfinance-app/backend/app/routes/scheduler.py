"""Scheduler control: list jobs, fire on-demand."""
from fastapi import APIRouter, HTTPException

from app.scheduler.manager import get_scheduler, configure_jobs


router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/jobs")
def list_jobs():
    s = get_scheduler()
    return [
        {"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
         "trigger": str(j.trigger)}
        for j in s.get_jobs()
    ]


@router.post("/reload")
def reload_jobs():
    configure_jobs()
    return {"ok": True}


@router.post("/run/{job_id}")
def run_now(job_id: str):
    s = get_scheduler()
    job = s.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    job.func()
    return {"ok": True}
