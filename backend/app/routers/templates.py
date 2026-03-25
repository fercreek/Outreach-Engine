"""Templates router — CRUD + spintax preview."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import MessageTemplate, Niche
from app.schemas import TemplateCreate, TemplateUpdate, TemplateRead, SpintaxPreview
from app.services.spintax import spin_multiple

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=list[TemplateRead])
def list_templates(
    niche: Optional[Niche] = None,
    active_only: bool = True,
    session: Session = Depends(get_session),
):
    query = select(MessageTemplate)
    if niche:
        query = query.where(MessageTemplate.niche == niche)
    if active_only:
        query = query.where(MessageTemplate.is_active == True)  # noqa: E712
    return session.exec(query).all()


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(template_id: int, session: Session = Depends(get_session)):
    tpl = session.get(MessageTemplate, template_id)
    if not tpl:
        raise HTTPException(404, "Template not found")
    return tpl


@router.post("/", response_model=TemplateRead, status_code=201)
def create_template(data: TemplateCreate, session: Session = Depends(get_session)):
    tpl = MessageTemplate.model_validate(data)
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(template_id: int, data: TemplateUpdate, session: Session = Depends(get_session)):
    tpl = session.get(MessageTemplate, template_id)
    if not tpl:
        raise HTTPException(404, "Template not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        for key, value in update_data.items():
            setattr(tpl, key, value)
        session.add(tpl)
        session.commit()
        session.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, session: Session = Depends(get_session)):
    tpl = session.get(MessageTemplate, template_id)
    if not tpl:
        raise HTTPException(404, "Template not found")
    session.delete(tpl)
    session.commit()


@router.post("/preview")
def preview_spintax(data: SpintaxPreview):
    """Generate N variations of a spintax template."""
    variations = spin_multiple(data.template_text, data.count)
    return {"variations": variations, "count": len(variations)}
