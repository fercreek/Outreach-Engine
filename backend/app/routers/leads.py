"""Leads router — CRUD + bulk import + status management."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session, select, func, col

from app.database import get_session
from app.models import Lead, LeadStatus, Niche, ActivityLog, ActionType, Blacklist, MessageTemplate
from app.schemas import LeadCreate, LeadUpdate, LeadRead, LeadBulkImport
from app.services.spintax import spin, personalize

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/", response_model=list[LeadRead])
def list_leads(
    status: Optional[LeadStatus] = None,
    niche: Optional[Niche] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """List leads with optional filters."""
    query = select(Lead)
    if status:
        query = query.where(Lead.status == status)
    if niche:
        query = query.where(Lead.niche == niche)
    if search:
        query = query.where(
            col(Lead.username).contains(search)
            | col(Lead.business_name).contains(search)
        )
    query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)  # type: ignore[union-attr]
    return session.exec(query).all()


@router.get("/count")
def count_leads(
    status: Optional[LeadStatus] = None,
    niche: Optional[Niche] = None,
    session: Session = Depends(get_session),
):
    """Get lead counts."""
    query = select(func.count(Lead.id))
    if status:
        query = query.where(Lead.status == status)
    if niche:
        query = query.where(Lead.niche == niche)
    total = session.exec(query).one()
    return {"count": total}


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: int, session: Session = Depends(get_session)):
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.post("/", response_model=LeadRead, status_code=201)
def create_lead(data: LeadCreate, session: Session = Depends(get_session)):
    # Check blacklist
    blacklisted = session.exec(
        select(Blacklist).where(Blacklist.username == data.username)
    ).first()
    if blacklisted:
        raise HTTPException(409, f"@{data.username} is blacklisted: {blacklisted.reason}")

    # Check duplicate
    existing = session.exec(
        select(Lead).where(Lead.username == data.username)
    ).first()
    if existing:
        raise HTTPException(409, f"@{data.username} already exists (id={existing.id})")

    lead = Lead.model_validate(data)
    session.add(lead)
    session.commit()
    session.refresh(lead)

    # Log discovery
    log = ActivityLog(
        lead_id=lead.id, 
        action_type=ActionType.discovered, 
        level="info",
        message=f"Lead @{lead.username} añadido manualmente"
    )
    session.add(log)
    session.commit()

    return lead


@router.post("/bulk", status_code=201)
def bulk_import(data: LeadBulkImport, session: Session = Depends(get_session)):
    """Import multiple leads at once, skipping blacklisted and duplicates."""
    created = 0
    skipped = 0
    errors: list[str] = []

    for item in data.leads:
        try:
            # Check blacklist & duplicates silently
            bl = session.exec(select(Blacklist).where(Blacklist.username == item.username)).first()
            if bl:
                skipped += 1
                continue
            existing = session.exec(select(Lead).where(Lead.username == item.username)).first()
            if existing:
                skipped += 1
                continue

            lead = Lead.model_validate(item)
            session.add(lead)
            session.commit()
            session.refresh(lead)

            log = ActivityLog(
                lead_id=lead.id, 
                action_type=ActionType.discovered,
                level="info",
                message=f"Lead @{lead.username} importado en lote"
            )
            session.add(log)
            session.commit()
            created += 1
        except Exception as e:
            errors.append(f"@{item.username}: {str(e)}")
            skipped += 1

    return {"created": created, "skipped": skipped, "errors": errors}


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(lead_id: int, data: LeadUpdate, session: Session = Depends(get_session)):
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        for key, value in update_data.items():
            setattr(lead, key, value)
        session.add(lead)
        session.commit()
        session.refresh(lead)

    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, session: Session = Depends(get_session)):
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    session.delete(lead)
    session.commit()


@router.post("/{lead_id}/transition")
def transition_status(
    lead_id: int,
    new_status: LeadStatus,
    session: Session = Depends(get_session),
):
    """Explicitly transition a lead to a new status."""
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")

    old_status = lead.status
    lead.status = new_status
    lead.updated_at = datetime.now(timezone.utc)
    if new_status in (LeadStatus.dm_sent, LeadStatus.interacted):
        lead.last_interaction_at = datetime.now(timezone.utc)

    session.add(lead)

    log = ActivityLog(
        lead_id=lead.id,
        action_type=ActionType.qualified,
        level="info",
        message=f"Estatus: {old_status} → {new_status}",
    )
    session.add(log)
    session.commit()
    session.refresh(lead)

    return {"id": lead.id, "old_status": old_status, "new_status": new_status}


# ── Approval Queue (Human-in-the-loop) ────────────────────────

@router.get("/approval-queue", response_model=list[dict])
def approval_queue(session: Session = Depends(get_session)):
    """
    Return all leads in 'qualified' or 'warming' status that are ready for DM review.
    Each entry includes a preview of the message that will be sent.
    """
    template = session.exec(select(MessageTemplate).where(MessageTemplate.is_active == True)).first()

    leads = session.exec(
        select(Lead).where(Lead.status.in_([LeadStatus.qualified, LeadStatus.warming]))
        .order_by(Lead.updated_at.desc())  # type: ignore[union-attr]
    ).all()

    result = []
    for lead in leads:
        preview = ""
        if template:
            raw = spin(template.content)
            preview = personalize(raw, lead.model_dump())
        result.append({
            "id": lead.id,
            "username": lead.username,
            "business_name": lead.business_name,
            "profile_url": lead.profile_url,
            "niche": lead.niche,
            "follower_count": lead.follower_count,
            "bio": lead.bio,
            "status": lead.status,
            "message_preview": preview,
            "updated_at": lead.updated_at,
        })
    return result


@router.post("/approval-queue/approve")
def approve_leads(
    lead_ids: list[int] = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Bulk-approve leads for DM dispatch: transitions them from qualified/warming → dm_pending.
    The worker will pick them up on the next job run.
    """
    approved = []
    for lead_id in lead_ids:
        lead = session.get(Lead, lead_id)
        if not lead:
            continue
        if lead.status not in (LeadStatus.qualified, LeadStatus.warming):
            continue
        lead.status = LeadStatus.dm_pending
        lead.updated_at = datetime.now(timezone.utc)
        session.add(lead)
        log = ActivityLog(
            lead_id=lead.id,
            action_type=ActionType.qualified,
            level="info",
            message="Lead aprobado para DM por operador",
        )
        session.add(log)
        approved.append(lead_id)

    session.commit()
    return {"approved": approved, "count": len(approved)}


@router.post("/approval-queue/reject")
def reject_leads(
    lead_ids: list[int] = Body(..., embed=True),
    reason: Optional[str] = Body(default="Rechazado por operador"),
    session: Session = Depends(get_session),
):
    """
    Bulk-reject leads: transitions them to 'excluded' so they won't be processed again.
    """
    rejected = []
    for lead_id in lead_ids:
        lead = session.get(Lead, lead_id)
        if not lead:
            continue
        lead.status = LeadStatus.excluded
        lead.updated_at = datetime.now(timezone.utc)
        session.add(lead)
        log = ActivityLog(
            lead_id=lead.id,
            action_type=ActionType.excluded,
            level="info",
            message=f"Lead excluido: {reason}",
        )
        session.add(log)
        rejected.append(lead_id)

    session.commit()
    return {"rejected": rejected, "count": len(rejected)}
