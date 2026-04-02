import base64
import logging
import urllib.error
import urllib.parse
import urllib.request

from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.models import ActivityLog, ActionType, Lead

logger = logging.getLogger(__name__)


def _log_escalation(lead_id: int, message: str) -> None:
    with Session(engine) as session:
        session.add(
            ActivityLog(
                job_id=None,
                lead_id=lead_id,
                level="warning",
                message=message[:500],
                action_type=ActionType.escalation,
            )
        )
        session.commit()


def notify_lead_converted(lead: Lead, notes: str) -> None:
    line = (
        f"✅ Lead convertido — @{lead.username} "
        f"({lead.business_name or lead.niche.value}) — {notes}"
    )
    logger.info(line)
    with Session(engine) as session:
        session.add(
            ActivityLog(
                job_id=None,
                lead_id=lead.id,
                level="success",
                message=line[:500],
                action_type=ActionType.agent_reply,
            )
        )
        session.commit()
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    frm = settings.twilio_whatsapp_from
    to = settings.escalation_whatsapp_to
    if not all([sid, token, frm, to]):
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    data = urllib.parse.urlencode(
        {"From": frm, "To": to, "Body": line[:1600]}
    ).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Basic {auth}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except Exception as e:
        logger.error(f"Twilio convert notify failed: {e}")


def send_whatsapp_escalation(lead: Lead, reason: str) -> dict:
    line = (
        f"Escalación Studio Link — @{lead.username} "
        f"({lead.business_name or 'sin nombre'}) — {reason}"
    )
    logger.warning(line)
    _log_escalation(lead.id, line)

    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    frm = settings.twilio_whatsapp_from
    to = settings.escalation_whatsapp_to

    if not all([sid, token, frm, to]):
        return {"sent": False, "channel": "log_only", "detail": line}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    data = urllib.parse.urlencode(
        {"From": frm, "To": to, "Body": line[:1600]}
    ).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Basic {auth}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return {"sent": True, "channel": "whatsapp", "detail": line}
    except urllib.error.HTTPError as e:
        logger.error(f"Twilio HTTP error: {e}")
        return {"sent": False, "error": str(e), "detail": line}
    except Exception as e:
        logger.error(f"Twilio send failed: {e}")
        return {"sent": False, "error": str(e), "detail": line}
