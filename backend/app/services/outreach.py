"""Outreach service — send DMs with human-like typing simulation."""

import logging

from playwright.async_api import Page

from app.services.browser import get_browser_page
from app.utils.jitter import human_pause, keystroke_delay_ms

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"


async def send_dm(username: str, message: str) -> dict:
    """
    Send a TikTok DM to a user with keystroke dynamics.
    Uses page.type() with random per-key delays to simulate human typing.

    Returns {success, username, message_sent, error}.
    """
    page = await get_browser_page()
    result = {"success": False, "username": username, "message_sent": "", "error": None}

    try:
        # ── Navigate to DM inbox ────────────────────────────
        await page.goto(f"{TIKTOK_BASE}/messages", wait_until="networkidle", timeout=30000)
        await human_pause(3, 6)

        # ── Open new message / search for user ──────────────
        # Click "New message" button
        new_msg_btn = page.locator('button:has-text("New message"), [data-e2e="new-message-btn"]').first
        if await new_msg_btn.count() > 0:
            await new_msg_btn.click()
            await human_pause(1.5, 3)

        # Search for the user
        search_input = page.locator('input[placeholder*="Search"], input[type="search"]').first
        if await search_input.count() > 0:
            await search_input.click()
            await human_pause(0.5, 1)

            # Type username with human-like delays
            for char in username:
                await search_input.type(char, delay=keystroke_delay_ms())

            await human_pause(2, 4)  # Wait for search results

            # Click on the user result
            user_result = page.locator(f'text=@{username}').first
            if await user_result.count() > 0:
                await user_result.click()
                await human_pause(1, 2)
            else:
                # Try clicking first result
                first_result = page.locator('[data-e2e="search-user-item"]').first
                if await first_result.count() > 0:
                    await first_result.click()
                    await human_pause(1, 2)
                else:
                    result["error"] = f"User @{username} not found in search"
                    logger.warning(f"⚠️ {result['error']}")
                    return result

        # ── Confirm / start chat ─────────────────────────────
        next_btn = page.locator('button:has-text("Next"), button:has-text("Chat")').first
        if await next_btn.count() > 0:
            await next_btn.click()
            await human_pause(2, 4)

        # ── Type the message ─────────────────────────────────
        msg_input = page.locator(
            '[data-e2e="message-input"], '
            '[contenteditable="true"], '
            'textarea[placeholder*="Send a message"]'
        ).first

        if await msg_input.count() == 0:
            result["error"] = "Could not find message input field"
            logger.error(f"❌ {result['error']}")
            return result

        await msg_input.click()
        await human_pause(0.5, 1.5)

        # Type with keystroke dynamics (the core anti-detection mechanism)
        for char in message:
            delay = keystroke_delay_ms()
            await msg_input.type(char, delay=delay)

        await human_pause(1, 3)

        # ── Send the message ─────────────────────────────────
        # Try Enter key first, fallback to send button
        await page.keyboard.press("Enter")
        await human_pause(2, 4)

        result["success"] = True
        result["message_sent"] = message
        logger.info(f"✉️ DM sent to @{username} ({len(message)} chars)")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ DM send error for @{username}: {e}")

    return result
