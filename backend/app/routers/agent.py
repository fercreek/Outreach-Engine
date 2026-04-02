from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.database import get_session
from app.models import ConversationMessage, Lead
from app.schemas import ConversationLeadSummary, ConversationMessageRead, ProcessReplyBody
from app.services.agent import process_reply_event

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/process-reply")
async def post_process_reply(body: ProcessReplyBody):
    result = await process_reply_event(body.lead_id, body.message_text)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "agent_failed"))
    return result


@router.get("/conversations", response_model=list[ConversationLeadSummary])
def list_conversation_leads(session: Session = Depends(get_session)):
    rows = session.exec(
        select(
            ConversationMessage.lead_id,
            func.max(ConversationMessage.created_at).label("last_at"),
        ).group_by(ConversationMessage.lead_id)
    ).all()
    if not rows:
        return []
    out: list[ConversationLeadSummary] = []
    for lid, last_at in rows:
        lead = session.get(Lead, lid)
        if not lead:
            continue
        out.append(
            ConversationLeadSummary(
                lead_id=lead.id,
                username=lead.username,
                business_name=lead.business_name,
                status=lead.status,
                last_message_at=last_at,
            )
        )
    out.sort(key=lambda x: x.last_message_at, reverse=True)
    return out


@router.get(
    "/conversations/{lead_id}/messages",
    response_model=list[ConversationMessageRead],
)
def get_conversation_messages(lead_id: int, session: Session = Depends(get_session)):
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    rows = session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.lead_id == lead_id)
        .order_by(col(ConversationMessage.created_at))
    ).all()
    return rows
