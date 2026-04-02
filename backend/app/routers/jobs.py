"""Batch Jobs router — start, stop, status of automation runs."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from app.database import get_session
from app.models import BatchJob, JobStatus, Lead, LeadStatus
from app.schemas import BatchJobCreate, BatchJobRead
from app.services.worker import execute_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=list[BatchJobRead])
def list_jobs(
    status: Optional[JobStatus] = None,
    session: Session = Depends(get_session),
):
    query = select(BatchJob).order_by(BatchJob.created_at.desc())  # type: ignore[union-attr]
    if status:
        query = query.where(BatchJob.status == status)
    return session.exec(query).all()


@router.get("/active", response_model=Optional[BatchJobRead])
def get_active_job(session: Session = Depends(get_session)):
    """Return the currently running job, if any."""
    job = session.exec(
        select(BatchJob).where(BatchJob.status == JobStatus.running)
    ).first()
    return job


@router.get("/{job_id}", response_model=BatchJobRead)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(BatchJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/", response_model=BatchJobRead, status_code=201)
def create_job(data: BatchJobCreate, session: Session = Depends(get_session)):
    # Check no job is already running
    running = session.exec(
        select(BatchJob).where(BatchJob.status == JobStatus.running)
    ).first()
    if running:
        raise HTTPException(409, f"Job #{running.id} is already running")

    # Count eligible leads
    if data.lead_ids:
        total = len(data.lead_ids)
    else:
        # Default: all leads in dm_pending status
        total = len(
            session.exec(
                select(Lead).where(Lead.status == LeadStatus.dm_pending)
            ).all()
        )

    job = BatchJob(
        job_type=data.job_type,
        total_leads=total,
        status=JobStatus.pending,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.post("/{job_id}/start", response_model=BatchJobRead)
def start_job(
    job_id: int, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    job = session.get(BatchJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.pending:
        raise HTTPException(400, f"Cannot start job in '{job.status}' status")

    job.status = JobStatus.running
    job.started_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(job)

    # Trigger background worker
    background_tasks.add_task(execute_job, job.id)
    
    return job


@router.post("/{job_id}/pause", response_model=BatchJobRead)
def pause_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(BatchJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.running:
        raise HTTPException(400, "Can only pause a running job")

    job.status = JobStatus.paused
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.post("/{job_id}/cancel", response_model=BatchJobRead)
def cancel_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(BatchJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status in (JobStatus.completed, JobStatus.cancelled):
        raise HTTPException(400, f"Job is already {job.status}")

    job.status = JobStatus.cancelled
    job.finished_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
