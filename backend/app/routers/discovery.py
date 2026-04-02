from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.discovery import discover_leads

router = APIRouter(prefix="/discovery", tags=["discovery"])


class DiscoveryRunBody(BaseModel):
    hashtag: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(50, ge=1, le=500)


@router.post("/run")
async def run_discovery(body: DiscoveryRunBody, background_tasks: BackgroundTasks):
    background_tasks.add_task(discover_leads, body.hashtag, body.limit)
    return {"status": "started", "hashtag": body.hashtag.strip().lstrip("#"), "limit": body.limit}
