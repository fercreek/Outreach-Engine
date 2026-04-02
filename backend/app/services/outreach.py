"""Outreach service — send DMs with human-like typing simulation."""

import logging

from playwright.async_api import Page

from app.utils.jitter import human_pause, keystroke_delay_ms
from app.models import Lead

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"

# Selector sets — TikTok changes its DOM regularly, so we try multiple per element
# and take the first one that matches. Update these when TikTok ships a new layout.
_NEW_MSG_SELECTORS = [
    '[data-e2e="new-message-btn"]',
    'button[aria-label*="new message" i]',
    'button[aria-label*="mensaje" i]',
    'div[data-e2e="dm-new-chat"]',
    # Text-based fallbacks (least stable)
    'button:has-text("New message")',
    'button:has-text("Nuevo mensaje")',
]

_SEARCH_INPUT_SELECTORS = [
    'input[data-e2e="search-user-input"]',
    'input[placeholder*="Search" i]',
    'input[placeholder*="Buscar" i]',
    'input[type="search"]',
]

_CONFIRM_BTN_SELECTORS = [
    'button[data-e2e="chat-confirm-btn"]',
    'button:has-text("Chat")',
    'button:has-text("Next")',
    'button:has-text("Siguiente")',
]

_MSG_INPUT_SELECTORS = [
    '[data-e2e="message-input"]',
    'div[contenteditable="true"][data-e2e]',
    # Broad fallback — only used if all above fail
    'div[contenteditable="true"]',
    'textarea[placeholder*="message" i]',
    'textarea[placeholder*="mensaje" i]',
]

_CHALLENGE_URL_PARTS = (
    "captcha",
    "verify",
    "challenge",
    "sec_sdk",
    "security_check",
    "rotatel",
    "slide",
)


async def detect_tiktok_challenge(page: Page) -> bool:
    try:
        url = (page.url or "").lower()
        if any(p in url for p in _CHALLENGE_URL_PARTS):
            return True
        for sel in (
            'iframe[src*="captcha" i]',
            'iframe[src*="challenge" i]',
            '[id*="captcha" i]',
            '[class*="captcha"]',
            '[data-e2e*="captcha" i]',
        ):
            loc = page.locator(sel).first
            try:
                if await loc.count() > 0 and await loc.is_visible(timeout=1500):
                    return True
            except Exception:
                continue
        body = await page.inner_text("body", timeout=8000)
        if body:
            low = body.lower()
            for needle in (
                "security check",
                "verify you",
                "slide to",
                "rotate the",
                "unusual traffic",
                "complete the puzzle",
                "select all",
                "prove you",
                "are you human",
                "captcha",
            ):
                if needle in low:
                    return True
    except Exception:
        pass
    return False


async def _first_visible(page: Page, selectors: list[str]):
    """Return the first locator that has at least one visible element, or None."""
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if await loc.count() > 0 and await loc.is_visible():
                return loc
        except Exception:
            continue
    return None


async def preflight_dm_tiktok(page: Page, lead: Lead, message: str) -> dict:
    username = lead.username
    result = {"success": False, "username": username, "error": None, "preflight": True}
    try:
        await page.goto(f"{TIKTOK_BASE}/messages", wait_until="networkidle", timeout=30_000)
        await human_pause(3, 6)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            return result
        new_msg_btn = await _first_visible(page, _NEW_MSG_SELECTORS)
        if not new_msg_btn:
            result["error"] = "No se encontró el botón de mensaje nuevo"
            return result
        await new_msg_btn.click()
        await human_pause(1.5, 3)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            return result
        search_input = await _first_visible(page, _SEARCH_INPUT_SELECTORS)
        if not search_input:
            result["error"] = "No se encontró el campo de búsqueda"
            return result
        await search_input.click()
        await human_pause(0.5, 1)
        for char in username:
            await search_input.type(char, delay=keystroke_delay_ms())
        await human_pause(2, 4)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            return result
        user_result = None
        for selector in [
            f'text=@{username}',
            f'[title="@{username}"]',
            '[data-e2e="search-user-item"]',
            '[data-e2e="dm-search-result-item"]',
            'ul[data-e2e] li:first-child',
        ]:
            loc = page.locator(selector).first
            try:
                if await loc.count() > 0 and await loc.is_visible():
                    user_result = loc
                    break
            except Exception:
                continue
        if not user_result:
            result["error"] = f"Usuario @{username} no aparece en la búsqueda"
            return result
        await user_result.click()
        await human_pause(1, 2)
        confirm_btn = await _first_visible(page, _CONFIRM_BTN_SELECTORS)
        if confirm_btn:
            await confirm_btn.click()
            await human_pause(2, 4)
        msg_input = await _first_visible(page, _MSG_INPUT_SELECTORS)
        if not msg_input:
            result["error"] = "No se encontró el campo de mensaje"
            return result
        await msg_input.click()
        await human_pause(0.5, 1.5)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            return result
        for char in message:
            await msg_input.type(char, delay=keystroke_delay_ms())
        await human_pause(1, 2)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            return result
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


async def send_dm(page: Page, lead: Lead, message: str) -> dict:
    """
    Send a TikTok DM to a user with keystroke dynamics.
    Returns {success, username, message_sent, error}.
    """
    username = lead.username
    result = {"success": False, "username": username, "message_sent": "", "error": None}

    try:
        # ── Navigate to DM inbox ────────────────────────────
        await page.goto(f"{TIKTOK_BASE}/messages", wait_until="networkidle", timeout=30_000)
        await human_pause(3, 6)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            logger.warning("⛔ TikTok challenge/CAPTCHA detectado — no se envía")
            return result

        # ── Open new message dialog ──────────────────────────
        new_msg_btn = await _first_visible(page, _NEW_MSG_SELECTORS)
        if new_msg_btn:
            await new_msg_btn.click()
            await human_pause(1.5, 3)
        else:
            result["error"] = "Could not find 'New message' button"
            logger.error(f"❌ {result['error']}")
            return result
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            logger.warning("⛔ TikTok challenge/CAPTCHA detectado — no se envía")
            return result

        # ── Search for user ──────────────────────────────────
        search_input = await _first_visible(page, _SEARCH_INPUT_SELECTORS)
        if not search_input:
            result["error"] = "Could not find search input"
            logger.error(f"❌ {result['error']}")
            return result

        await search_input.click()
        await human_pause(0.5, 1)

        # Type username with human-like per-keystroke delays
        for char in username:
            await search_input.type(char, delay=keystroke_delay_ms())

        await human_pause(2, 4)  # Wait for search results to populate
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            logger.warning("⛔ TikTok challenge/CAPTCHA detectado — no se envía")
            return result

        # Click the user result — TikTok may show display name OR @username,
        # so we try both and fall back to the first result item.
        user_result = None
        for selector in [
            f'text=@{username}',
            f'[title="@{username}"]',
            '[data-e2e="search-user-item"]',
            '[data-e2e="dm-search-result-item"]',
            # Catch-all: first list item in the results container
            'ul[data-e2e] li:first-child',
        ]:
            loc = page.locator(selector).first
            try:
                if await loc.count() > 0 and await loc.is_visible():
                    user_result = loc
                    break
            except Exception:
                continue

        if not user_result:
            result["error"] = f"User @{username} not found in search results"
            logger.warning(f"⚠️ {result['error']}")
            return result

        await user_result.click()
        await human_pause(1, 2)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            logger.warning("⛔ TikTok challenge/CAPTCHA detectado — no se envía")
            return result

        # ── Confirm / start chat ─────────────────────────────
        confirm_btn = await _first_visible(page, _CONFIRM_BTN_SELECTORS)
        if confirm_btn:
            await confirm_btn.click()
            await human_pause(2, 4)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            logger.warning("⛔ TikTok challenge/CAPTCHA detectado — no se envía")
            return result

        # ── Locate message input ─────────────────────────────
        msg_input = await _first_visible(page, _MSG_INPUT_SELECTORS)
        if not msg_input:
            result["error"] = "Could not find message input field"
            logger.error(f"❌ {result['error']}")
            return result

        await msg_input.click()
        await human_pause(0.5, 1.5)

        # Type with per-keystroke delays (core anti-detection mechanism)
        for char in message:
            await msg_input.type(char, delay=keystroke_delay_ms())

        await human_pause(1, 3)
        if await detect_tiktok_challenge(page):
            result["error"] = "challenge_detected"
            result["challenge_detected"] = True
            logger.warning("⛔ TikTok challenge/CAPTCHA detectado — no se envía")
            return result

        # ── Send ─────────────────────────────────────────────
        await page.keyboard.press("Enter")
        await human_pause(2, 4)

        result["success"] = True
        result["message_sent"] = message
        logger.info(f"✉️ DM sent to @{username} ({len(message)} chars)")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ DM send error for @{username}: {e}")

    return result
