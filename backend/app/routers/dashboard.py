"""Dashboard router — aggregate stats for the control panel."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.database import get_session
from app.models import Lead, LeadStatus, Niche, ActivityLog, ActionType, BatchJob, JobStatus
from app.schemas import DashboardStats, BatchJobRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(session: Session = Depends(get_session)):
    # Total leads
    total = session.exec(select(func.count(Lead.id))).one() or 0

    # By status
    by_status: dict[str, int] = {}
    for status in LeadStatus:
        count = session.exec(
            select(func.count(Lead.id)).where(Lead.status == status)
        ).one() or 0
        if count > 0:
            by_status[status.value] = count

    # By niche
    by_niche: dict[str, int] = {}
    for niche in Niche:
        count = session.exec(
            select(func.count(Lead.id)).where(Lead.niche == niche)
        ).one() or 0
        if count > 0:
            by_niche[niche.value] = count

    # DMs sent today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    dms_today = session.exec(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.action_type == ActionType.dm_sent,
            ActivityLog.created_at >= today_start,
        )
    ).one() or 0

    # Replies today
    replies_today = session.exec(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.action_type == ActionType.reply_detected,
            ActivityLog.created_at >= today_start,
        )
    ).one() or 0

    # Active job
    active_job_row = session.exec(
        select(BatchJob).where(BatchJob.status == JobStatus.running)
    ).first()

    active_job = None
    if active_job_row:
        active_job = BatchJobRead.model_validate(active_job_row)

    return DashboardStats(
        total_leads=total,
        by_status=by_status,
        by_niche=by_niche,
        dms_sent_today=dms_today,
        replies_today=replies_today,
        active_job=active_job,
    )
