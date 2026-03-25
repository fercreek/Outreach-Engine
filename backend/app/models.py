"""Database models — the core schema for the outreach engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


# ── Enums ────────────────────────────────────────────────────

class LeadStatus(str, Enum):
    discovered = "discovered"
    qualified = "qualified"
    warming = "warming"
    interacted = "interacted"
    dm_pending = "dm_pending"       # awaiting human approval
    dm_sent = "dm_sent"
    replied = "replied"
    converted = "converted"
    excluded = "excluded"


class Niche(str, Enum):
    danza = "danza"
    futbol = "futbol"
    pilates = "pilates"
    gym = "gym"
    yoga = "yoga"
    artes_marciales = "artes_marciales"
    musica = "musica"
    otros = "otros"


class ActionType(str, Enum):
    discovered = "discovered"
    qualified = "qualified"
    profile_visited = "profile_visited"
    video_watched = "video_watched"
    liked = "liked"
    dm_sent = "dm_sent"
    reply_detected = "reply_detected"
    excluded = "excluded"
    error = "error"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# ── Models ───────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


class Lead(SQLModel, table=True):
    __tablename__ = "leads"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=100)
    business_name: Optional[str] = Field(default=None, max_length=255)
    profile_url: str = Field(max_length=500)
    niche: Niche = Field(default=Niche.otros)
    follower_count: Optional[int] = Field(default=None)
    bio: Optional[str] = Field(default=None, max_length=1000)
    status: LeadStatus = Field(default=LeadStatus.discovered, index=True)
    custom_message: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    last_interaction_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class MessageTemplate(SQLModel, table=True):
    __tablename__ = "message_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    niche: Optional[Niche] = Field(default=None, index=True)
    template_text: str
    spintax_enabled: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ActivityLog(SQLModel, table=True):
    __tablename__ = "activity_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    lead_id: Optional[int] = Field(default=None, foreign_key="leads.id", index=True)
    action_type: ActionType
    details: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)


class Blacklist(SQLModel, table=True):
    __tablename__ = "blacklist"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=100)
    reason: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=_now)


class BatchJob(SQLModel, table=True):
    __tablename__ = "batch_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    status: JobStatus = Field(default=JobStatus.pending)
    job_type: str = Field(default="outreach", max_length=50)  # outreach | discovery | warming
    total_leads: int = Field(default=0)
    processed: int = Field(default=0)
    failed: int = Field(default=0)
    config_json: Optional[str] = Field(default=None)   # JSON blob for job-specific settings
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)
