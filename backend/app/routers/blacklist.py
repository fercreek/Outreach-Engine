"""Blacklist router — prevent contacting excluded accounts."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import Blacklist, Lead, LeadStatus
from app.schemas import BlacklistCreate, BlacklistRead

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.get("/", response_model=list[BlacklistRead])
def list_blacklist(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    query = select(Blacklist)
    if search:
        query = query.where(Blacklist.username.contains(search))  # type: ignore
    query = query.offset(skip).limit(limit)
    return session.exec(query).all()


@router.post("/", response_model=BlacklistRead, status_code=201)
def add_to_blacklist(data: BlacklistCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Blacklist).where(Blacklist.username == data.username)).first()
    if existing:
        raise HTTPException(409, f"@{data.username} is already blacklisted")

    entry = Blacklist.model_validate(data)
    session.add(entry)

    # Also exclude any existing lead with this username
    lead = session.exec(select(Lead).where(Lead.username == data.username)).first()
    if lead:
        lead.status = LeadStatus.excluded
        session.add(lead)

    session.commit()
    session.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def remove_from_blacklist(entry_id: int, session: Session = Depends(get_session)):
    entry = session.get(Blacklist, entry_id)
    if not entry:
        raise HTTPException(404, "Blacklist entry not found")
    session.delete(entry)
    session.commit()
