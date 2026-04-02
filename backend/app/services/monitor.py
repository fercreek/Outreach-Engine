import asyncio
import logging
import re
from datetime import datetime, timezone

from playwright.async_api import Page
from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models import ActivityLog, ActionType, Lead, LeadStatus
from app.services.browser import get_browser_page
from app.services.worker import interruptible_sleep
from app.utils.jitter import human_pause

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"


async def _schedule_agent_reply(lead_id: int, preview: str) -> None:
    try:
        from app.services.agent import process_reply_event

        await process_reply_event(lead_id, preview)
    except Exception as ex:
        logger.error(f"Agent post-reply failed: {ex}")

_CONVERSATION_ROW_SELECTORS = [
    '[data-e2e="chat-list-item"]',
    '[data-e2e="message-list-item"]',
    'div[class*="ConversationItem"]',
    'div[class*="ChatListItem"]',
    'li[class*="chat-item"]',
    'div[role="listitem"]',
]

_USERNAME_IN_ROW_SELECTORS = [
    'a[href*="/@"]',
    '[data-e2e="message-username"]',
    'span[class*="username"]',
    'p[class*="Title"]',
]

_UNREAD_SELECTORS = [
    '[class*="unread"]',
    '[class*="Unread"]',
    '[data-e2e="message-unread-badge"]',
    'div[class*="Badge"]',
    'span[class*="badge"]',
]

_PREVIEW_SELECTORS = [
    '[class*="preview"]',
    '[class*="Preview"]',
    '[class*="lastMessage"]',
    '[class*="subtitle"]',
    'span[class*="desc"]',
]


def _normalize_username(raw: str) -> str:
    t = raw.strip().lstrip("@")
    t = re.sub(r"\s+", "", t)
    return t


def _username_from_href(href: str) -> str | None:
    if not href or "/@" not in href:
        return None
    m = re.search(r"/@([^/?#]+)", href)
    if not m:
        return None
    return m.group(1).strip()


async def _extract_row_username(row) -> str:
    for sel in _USERNAME_IN_ROW_SELECTORS:
        try:
            loc = row.locator(sel).first
            if await loc.count() > 0:
                href = await loc.get_attribute("href")
                if href:
                    u = _username_from_href(href)
                    if u:
                        return u
                text = await loc.inner_text()
                nu = _normalize_username(text)
                if nu and not nu.isspace():
                    return nu
        except Exception:
            continue
    return ""


async def _row_has_unread(row) -> bool:
    for sel in _UNREAD_SELECTORS:
        try:
            loc = row.locator(sel).first
            if await loc.count() > 0:
                vis = await loc.is_visible()
                if vis:
                    return True
        except Exception:
            continue
    return False


def _log_reply(lead_id: int, message: str):
    with Session(engine) as session:
        session.add(
            ActivityLog(
                job_id=None,
                lead_id=lead_id,
                level="success",
                message=message[:500],
                action_type=ActionType.reply_detected,
            )
        )
        session.commit()


def _update_lead_replied(lead_id: int) -> None:
    with Session(engine) as session:
        lead = session.get(Lead, lead_id)
        if lead and lead.status == LeadStatus.dm_sent:
            lead.status = LeadStatus.replied
            lead.updated_at = datetime.now(timezone.utc)
            lead.last_interaction_at = datetime.now(timezone.utc)
            session.add(lead)
            session.commit()


async def check_inbox_for_replies(page: Page | None = None) -> list[dict]:
    own_page = page is None
    if own_page:
        page = await get_browser_page()

    results: list[dict] = []

    try:
        await page.goto(f"{TIKTOK_BASE}/messages", wait_until="networkidle", timeout=45_000)
        await human_pause(3.0, 6.0)

        with Session(engine) as session:
            dm_sent = session.exec(
                select(Lead).where(Lead.status == LeadStatus.dm_sent)
            ).all()
        by_user = {l.username.lower(): l.id for l in dm_sent}

        if not by_user:
            logger.info("Monitor: no leads with status dm_sent")
            return results

        rows_found: list = []
        for sel in _CONVERSATION_ROW_SELECTORS:
            try:
                loc = page.locator(sel)
                cnt = await loc.count()
                if cnt > 0:
                    for i in range(min(cnt, 200)):
                        rows_found.append(loc.nth(i))
                    break
            except Exception:
                continue

        for row in rows_found:
            try:
                username = await _extract_row_username(row)
                if not username:
                    continue
                key = username.lower()
                if key not in by_user:
                    continue
                if not await _row_has_unread(row):
                    continue
                lead_id = by_user[key]
                preview = ""
                for ps in _PREVIEW_SELECTORS:
                    try:
                        pel = row.locator(ps).first
                        if await pel.count() > 0:
                            preview = (await pel.inner_text()).strip()
                            break
                    except Exception:
                        continue
                _update_lead_replied(lead_id)
                _log_reply(
                    lead_id,
                    f"Respuesta detectada de @{username}: {preview[:120]}",
                )
                results.append(
                    {
                        "username": username,
                        "lead_id": lead_id,
                        "preview": preview,
                    }
                )
                logger.info(f"Monitor: reply from @{username} (lead {lead_id})")
                if settings.anthropic_api_key and settings.agent_auto_on_reply:
                    asyncio.create_task(_schedule_agent_reply(lead_id, preview))
            except Exception as e:
                logger.warning(f"Monitor row error: {e}")
                continue

        logger.info(f"Monitor: {len(results)} replies processed")

    except Exception as e:
        logger.error(f"Monitor inbox error: {e}")
        with Session(engine) as session:
            session.add(
                ActivityLog(
                    job_id=None,
                    lead_id=None,
                    level="error",
                    message=f"Monitor error: {str(e)[:450]}",
                    action_type=ActionType.error,
                )
            )
            session.commit()

    finally:
        if own_page and page and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass

    return results


async def poll_replies_forever() -> None:
    while True:
        await check_inbox_for_replies()
        await interruptible_sleep(None, 600.0)
