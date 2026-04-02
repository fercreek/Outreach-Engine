"""Pydantic schemas (DTOs) for API request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import ActionType, JobStatus, LeadStatus, Niche


# ── Leads ────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    username: str = Field(max_length=100)
    business_name: Optional[str] = None
    profile_url: str
    niche: Niche = Niche.otros
    follower_count: Optional[int] = None
    bio: Optional[str] = None
    custom_message: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    business_name: Optional[str] = None
    niche: Optional[Niche] = None
    follower_count: Optional[int] = None
    bio: Optional[str] = None
    status: Optional[LeadStatus] = None
    custom_message: Optional[str] = None
    notes: Optional[str] = None


class LeadRead(BaseModel):
    id: int
    username: str
    business_name: Optional[str]
    profile_url: str
    niche: Niche
    follower_count: Optional[int]
    bio: Optional[str]
    status: LeadStatus
    custom_message: Optional[str]
    notes: Optional[str]
    last_interaction_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class LeadBulkImport(BaseModel):
    leads: list[LeadCreate]


# ── Templates ────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str = Field(max_length=120)
    niche: Optional[Niche] = None
    content: str
    spintax_enabled: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    niche: Optional[Niche] = None
    content: Optional[str] = None
    spintax_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class TemplateRead(BaseModel):
    id: int
    name: str
    niche: Optional[Niche]
    content: str
    spintax_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SpintaxPreview(BaseModel):
    content: str
    count: int = Field(default=5, ge=1, le=20)


# ── Blacklist ────────────────────────────────────────────────

class BlacklistCreate(BaseModel):
    username: str = Field(max_length=100)
    reason: Optional[str] = None


class BlacklistRead(BaseModel):
    id: int
    username: str
    reason: Optional[str]
    created_at: datetime


# ── Activity Log ─────────────────────────────────────────────

class ActivityLogRead(BaseModel):
    id: int
    job_id: Optional[int]
    lead_id: Optional[int]
    action_type: ActionType
    level: str
    message: str
    created_at: datetime


# ── Batch Jobs ───────────────────────────────────────────────

class BatchJobCreate(BaseModel):
    job_type: str = "outreach"
    lead_ids: list[int] = Field(default_factory=list)


class BatchJobRead(BaseModel):
    id: int
    status: JobStatus
    job_type: str
    total_leads: int
    leads_processed: int
    leads_failed: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime


# ── Dashboard Stats ──────────────────────────────────────────

class DashboardStats(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    by_niche: dict[str, int]
    dms_sent_today: int
    replies_today: int
    active_job: Optional[BatchJobRead] = None


class ConversationMessageRead(BaseModel):
    id: int
    lead_id: int
    role: str
    content: str
    created_at: datetime


class ConversationLeadSummary(BaseModel):
    lead_id: int
    username: str
    business_name: Optional[str]
    status: LeadStatus
    last_message_at: datetime


class ProcessReplyBody(BaseModel):
    lead_id: int = Field(ge=1)
    message_text: Optional[str] = Field(default=None, max_length=8000)
