import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic
from sqlmodel import Session, col, select

from app.config import settings
from app.database import engine
from app.models import ActivityLog, ActionType, ConversationMessage, Lead, LeadStatus
from app.services.notifications import notify_lead_converted, send_whatsapp_escalation

logger = logging.getLogger(__name__)

_TOOLS = [
    {
        "name": "get_lead_context",
        "description": "Obtiene datos del lead: username, negocio, nicho, bio, seguidores, estado.",
        "input_schema": {
            "type": "object",
            "properties": {"lead_id": {"type": "integer"}},
            "required": ["lead_id"],
        },
    },
    {
        "name": "send_reply",
        "description": "Envía un mensaje DM al usuario en TikTok (usa el navegador automatizado).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "message": {"type": "string"},
            },
            "required": ["lead_id", "message"],
        },
    },
    {
        "name": "mark_converted",
        "description": "Marca el lead como convertido (trial o interés cerrado).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["lead_id", "notes"],
        },
    },
    {
        "name": "mark_excluded",
        "description": "Marca el lead como excluido (sin interés o rechazo claro).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["lead_id", "reason"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escala a Fernando (WhatsApp si está configurado, si no solo log).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["lead_id", "reason"],
        },
    },
]


def _load_knowledge_base() -> str:
    base = Path(__file__).resolve().parent.parent / "knowledge"
    parts: list[str] = []
    for name in (
        "studio-link-overview.md",
        "plans-pricing.md",
        "faq.md",
        "trial-signup.md",
    ):
        p = base / name
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def _build_system_prompt() -> str:
    kb = _load_knowledge_base()
    trial = ""
    if settings.trial_signup_url:
        trial = f"\nURL de registro trial (úsala cuando corresponda): {settings.trial_signup_url}\n"
    return (
        "Eres el equipo de Studio Link (software para academias, estudios y gimnasios).\n"
        "Objetivo: entender el negocio del lead y ayudar con claridad, sin ser agresivo.\n"
        "No inventes precios exactos. Si preguntan cifras, orienta al trial o a revisar planes en la web.\n"
        "Si la conversación requiere un humano, usa escalate_to_human.\n"
        f"{trial}\n"
        "Referencia de producto:\n"
        f"{kb}"
    )


def _serialize_assistant_blocks(content) -> list[dict]:
    out: list[dict] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            out.append({"type": "text", "text": block.text})
        elif getattr(block, "type", None) == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
    return out


def _tool_get_lead_context(lead_id: int) -> dict:
    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"error": "not_found"}
        return {
            "username": lead.username,
            "business_name": lead.business_name,
            "niche": lead.niche.value if lead.niche else None,
            "bio": lead.bio,
            "follower_count": lead.follower_count,
            "status": lead.status.value,
            "notes": lead.notes,
            "profile_url": lead.profile_url,
            "trial_signup_url": settings.trial_signup_url,
        }


async def _tool_send_reply(lead_id: int, message: str) -> dict:
    from app.services.browser import get_browser_page
    from app.services.outreach import send_dm

    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"ok": False, "error": "Lead not found"}
        uname = lead.username
        payload = lead.model_dump()

    lead_dm = Lead(**payload)
    page = await get_browser_page()
    result = await send_dm(page, lead_dm, message)
    if result.get("success"):
        with Session(engine) as session:
            session.add(
                ActivityLog(
                    job_id=None,
                    lead_id=lead_id,
                    level="success",
                    message=f"Agent DM → @{uname}: {message[:200]}",
                    action_type=ActionType.agent_reply,
                )
            )
            session.commit()
    return result


def _tool_mark_converted(lead_id: int, notes: str) -> dict:
    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"ok": False, "error": "not_found"}
        lead.status = LeadStatus.converted
        lead.notes = notes
        lead.updated_at = datetime.now(timezone.utc)
        session.add(lead)
        session.commit()
        notify_lead_converted(lead, notes)
    return {"ok": True}


def _tool_mark_excluded(lead_id: int, reason: str) -> dict:
    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"ok": False, "error": "not_found"}
        lead.status = LeadStatus.excluded
        lead.notes = reason
        lead.updated_at = datetime.now(timezone.utc)
        session.add(lead)
        session.commit()
    return {"ok": True}


def _tool_escalate(lead_id: int, reason: str) -> dict:
    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"ok": False, "error": "not_found"}
        return send_whatsapp_escalation(lead, reason)


async def _dispatch_tool(name: str, payload: dict) -> dict:
    if name == "get_lead_context":
        return _tool_get_lead_context(int(payload["lead_id"]))
    if name == "send_reply":
        return await _tool_send_reply(int(payload["lead_id"]), str(payload["message"]))
    if name == "mark_converted":
        return _tool_mark_converted(int(payload["lead_id"]), str(payload["notes"]))
    if name == "mark_excluded":
        return _tool_mark_excluded(int(payload["lead_id"]), str(payload["reason"]))
    if name == "escalate_to_human":
        return _tool_escalate(int(payload["lead_id"]), str(payload["reason"]))
    return {"error": f"unknown_tool:{name}"}


def _load_history_rows(lead_id: int) -> list[ConversationMessage]:
    with Session(engine) as session:
        rows = session.exec(
            select(ConversationMessage)
            .where(ConversationMessage.lead_id == lead_id)
            .order_by(col(ConversationMessage.created_at))
        ).all()
        return list(rows)


def _rows_to_messages(rows: list[ConversationMessage]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        if r.role not in ("user", "assistant"):
            continue
        out.append({"role": r.role, "content": r.content})
    return out


def _append_message(lead_id: int, role: str, content: str) -> None:
    with Session(engine) as session:
        session.add(
            ConversationMessage(lead_id=lead_id, role=role, content=content[:10000])
        )
        session.commit()


async def process_reply_event(
    lead_id: int,
    inbound_message: str | None = None,
) -> dict:
    if not settings.anthropic_api_key:
        return {"ok": False, "error": "anthropic_api_key not configured"}

    text_in = (inbound_message or "").strip() or "(mensaje entrante sin texto; revisa el inbox de TikTok)"

    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"ok": False, "error": "lead not found"}
        if lead.status not in (LeadStatus.replied, LeadStatus.dm_sent):
            return {"ok": False, "error": f"invalid status: {lead.status}"}

    _append_message(lead_id, "user", text_in)

    rows = _load_history_rows(lead_id)
    messages = _rows_to_messages(rows)

    client = Anthropic(api_key=settings.anthropic_api_key)
    system = _build_system_prompt()

    max_rounds = 12
    for _ in range(max_rounds):
        resp = await asyncio.to_thread(
            lambda m=messages: client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=system,
                tools=_TOOLS,
                messages=m,
            )
        )

        if resp.stop_reason == "end_turn":
            parts: list[str] = []
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    parts.append(block.text)
            final = "\n".join(parts).strip()
            if final:
                _append_message(lead_id, "assistant", final)
            return {"ok": True, "assistant_text": final}

        if resp.stop_reason != "tool_use":
            return {"ok": False, "error": f"stop_reason:{resp.stop_reason}"}

        assistant_payload = _serialize_assistant_blocks(resp.content)
        messages.append({"role": "assistant", "content": assistant_payload})

        tool_payload: list[dict] = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            out = await _dispatch_tool(block.name, block.input)
            tool_payload.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(out, ensure_ascii=False),
                }
            )

        if not tool_payload:
            return {"ok": False, "error": "tool_use without blocks"}

        messages.append({"role": "user", "content": tool_payload})

    return {"ok": False, "error": "max_tool_rounds"}
