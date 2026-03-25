"""Reply monitor — check TikTok inbox for responses."""

import logging
from typing import Optional

from playwright.async_api import Page

from app.services.browser import get_browser_page
from app.utils.jitter import human_pause

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"


async def check_replies(known_usernames: list[str]) -> list[dict]:
    """
    Check the TikTok inbox for unread replies from known leads.
    Returns list of {username, has_reply, preview_text}.
    """
    page = await get_browser_page()
    replies: list[dict] = []

    try:
        await page.goto(f"{TIKTOK_BASE}/messages", wait_until="networkidle", timeout=30000)
        await human_pause(3, 6)

        # Look for conversation items with unread indicators
        conversations = await page.locator(
            '[data-e2e="message-list-item"], '
            '[class*="conversation"], '
            '[class*="ChatListItem"]'
        ).all()

        for conv in conversations:
            try:
                # Extract username from conversation
                username_el = conv.locator('a[href*="/@"], [class*="username"]').first
                if await username_el.count() == 0:
                    continue

                text = await username_el.inner_text()
                username = text.strip().lstrip("@")

                if username not in known_usernames:
                    continue

                # Check for unread badge
                unread_badge = conv.locator('[class*="unread"], [class*="badge"]')
                has_unread = await unread_badge.count() > 0

                # Get preview text
                preview_el = conv.locator('[class*="preview"], [class*="lastMessage"]').first
                preview = ""
                if await preview_el.count() > 0:
                    preview = await preview_el.inner_text()

                if has_unread:
                    replies.append({
                        "username": username,
                        "has_reply": True,
                        "preview_text": preview.strip(),
                    })
                    logger.info(f"💬 Reply detected from @{username}: {preview[:50]}...")

            except Exception as conv_err:
                logger.warning(f"⚠️ Error processing conversation: {conv_err}")
                continue

        logger.info(f"📬 Checked inbox: {len(replies)} new replies found")

    except Exception as e:
        logger.error(f"❌ Reply check error: {e}")

    return replies
