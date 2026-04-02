"""Activity Logs router — read + SSE streaming for live console."""

from typing import Optional
import asyncio
import json

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from sse_starlette.sse import EventSourceResponse

from app.database import get_session, engine
from app.models import ActivityLog, ActionType

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/")
def list_logs(
    lead_id: Optional[int] = None,
    action_type: Optional[ActionType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    query = select(ActivityLog)
    if lead_id:
        query = query.where(ActivityLog.lead_id == lead_id)
    if action_type:
        query = query.where(ActivityLog.action_type == action_type)
    query = query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit)  # type: ignore[union-attr]
    return session.exec(query).all()


@router.get("/stream")
async def stream_logs():
    """SSE endpoint for real-time activity log streaming."""
    last_id = 0

    async def event_generator():
        nonlocal last_id
        # Get initial max ID
        with Session(engine) as session:
            result = session.exec(select(func.max(ActivityLog.id)))
            max_id = result.one()
            last_id = max_id or 0

        while True:
            await asyncio.sleep(2)  # Poll every 2 seconds
            with Session(engine) as session:
                query = (
                    select(ActivityLog)
                    .where(ActivityLog.id > last_id)
                    .order_by(ActivityLog.id)
                    .limit(20)
                )
                new_logs = session.exec(query).all()
                for log in new_logs:
                    last_id = log.id  # type: ignore[assignment]
                    yield {
                        "event": "log",
                        "data": json.dumps({
                            "id": log.id,
                            "job_id": log.job_id,
                            "lead_id": log.lead_id,
                            "action_type": log.action_type.value,
                            "level": log.level,
                            "message": log.message,
                            "created_at": log.created_at.isoformat(),
                        }),
                    }

    return EventSourceResponse(event_generator())
