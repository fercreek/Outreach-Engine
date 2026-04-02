"""Instagram outreach service — send DMs via Playwright with Lexical editor injection.

Key discovery (2026-04-01):
  Instagram's message composer uses the Lexical editor (React). Standard DOM
  manipulation (execCommand, ClipboardEvent) is unreliable. The only robust path is:

  1. Seed a text node via execCommand('insertText', 'x') — creates the internal
     Lexical TextNode if the editor is empty.
  2. Overwrite it via the Lexical JS API:
       editor.update(() => { textNode.getWritable().__text = message }, {discrete:true})
  3. Click [aria-label="Send"].

  See docs/claude-code-vs-outreach-engine.md for the full session analysis.
"""

import logging

from playwright.async_api import Page

from app.utils.jitter import human_pause, keystroke_delay_ms
from app.models import Lead

logger = logging.getLogger(__name__)

IG_BASE = "https://www.instagram.com"

# ── Selector fallbacks ────────────────────────────────────────────────────────
# Instagram changes class names frequently; text/aria selectors are more stable.

_MSG_BUTTON_SELECTORS = [
    'button:has-text("Message")',
    'button:has-text("Mensaje")',
    '[role="button"]:has-text("Message")',
    '[role="button"]:has-text("Mensaje")',
]

_TEXTBOX_SELECTORS = [
    'div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"]',
]

_SEND_BUTTON_SELECTORS = [
    '[aria-label="Send"]',
    '[aria-label="Enviar"]',
    'button:has-text("Send")',
    'button:has-text("Enviar")',
]

# ── JS helpers (injected via page.evaluate) ───────────────────────────────────

_JS_SEED_TEXT_NODE = """
() => {
    const textbox = document.querySelector('div[contenteditable="true"][role="textbox"]');
    if (!textbox) return {ok: false, error: 'no textbox'};
    const editor = textbox.__lexicalEditor;
    if (!editor) return {ok: false, error: 'no lexical editor'};
    let hasTextNode = false;
    editor.read(() => {
        editor.getEditorState()._nodeMap.forEach(n => {
            if (n.__type === 'text') hasTextNode = true;
        });
    });
    if (!hasTextNode) {
        textbox.focus();
        textbox.click();
        document.execCommand('insertText', false, 'x');
    }
    return {seeded: !hasTextNode, hadText: hasTextNode};
}
"""

_JS_SET_LEXICAL_TEXT = """
(message) => {
    const textbox = document.querySelector('div[contenteditable="true"][role="textbox"]');
    if (!textbox) return {ok: false, error: 'no textbox'};
    const editor = textbox.__lexicalEditor;
    if (!editor) return {ok: false, error: 'no lexical editor'};

    // Find the text node key
    let textKey = null;
    editor.read(() => {
        editor.getEditorState()._nodeMap.forEach((n, k) => {
            if (n.__type === 'text') textKey = k;
        });
    });
    if (!textKey) return {ok: false, error: 'text node not found after seed'};

    // Overwrite via Lexical's writable mutation
    editor.update(() => {
        const node = editor.getEditorState()._nodeMap.get(textKey);
        node.getWritable().__text = message;
    }, {discrete: true});

    const content = textbox.__lexicalTextContent || textbox.textContent;
    return {ok: content === message, length: content.length};
}
"""

_JS_VERIFY_SENT = """
() => {
    const textbox = document.querySelector('div[contenteditable="true"][role="textbox"]');
    return {empty: !textbox || textbox.textContent.length === 0};
}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _first_visible(page: Page, selectors: list[str]):
    """Return the first locator with at least one visible element, or None."""
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if await loc.count() > 0 and await loc.is_visible(timeout=2_000):
                return loc
        except Exception:
            continue
    return None


async def preflight_dm_instagram(page: Page, lead: Lead, message: str) -> dict:
    username = lead.username
    result = {
        "success": False,
        "username": username,
        "error": None,
        "platform": "instagram",
        "preflight": True,
    }
    try:
        profile_url = f"{IG_BASE}/{username}/"
        await page.goto(profile_url, wait_until="load", timeout=45_000)
        try:
            await page.wait_for_selector(
                'button:has-text("Message"), button:has-text("Mensaje"), button:has-text("Follow"), button:has-text("Seguir")',
                timeout=10_000,
            )
        except Exception:
            pass
        await human_pause(2, 4)
        await page.evaluate("window.scrollBy(0, 220)")
        await human_pause(1.2, 2.5)
        await page.evaluate("window.scrollBy(0, -100)")
        await human_pause(0.5, 1.5)
        msg_btn = await _first_visible(page, _MSG_BUTTON_SELECTORS)
        if not msg_btn:
            result["error"] = (
                f"'Message' no encontrado en @{username} — privado, no existe o requiere seguir"
            )
            return result
        await msg_btn.click()
        await human_pause(1.5, 3)
        textbox = await _first_visible(page, _TEXTBOX_SELECTORS)
        if not textbox:
            result["error"] = "Panel DM no abrió — sin textbox"
            return result
        tb_locator = page.locator('div[contenteditable="true"][role="textbox"]').first
        await tb_locator.click()
        await human_pause(0.3, 0.6)
        await page.keyboard.type("x")
        await human_pause(0.6, 1.0)
        inject_result = await page.evaluate(_JS_SET_LEXICAL_TEXT, message)
        if not inject_result.get("ok"):
            result["error"] = f"Lexical: {inject_result.get('error')}"
            return result
        await human_pause(0.8, 1.5)
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

async def send_dm_instagram(page: Page, lead: Lead, message: str) -> dict:
    """
    Send an Instagram DM using Lexical editor injection.

    Flow:
      1. Navigate to instagram.com/{username}/
      2. Simulate human scroll (2-3 sec)
      3. Click "Message" button → DM panel opens
      4. Inject message via Lexical JS API
      5. Click Send / Enter
      6. Verify textbox is empty (message was accepted)

    Returns:
      {success: bool, username: str, message_sent: str, error: str|None}
    """
    username = lead.username
    result = {
        "success": False,
        "username": username,
        "message_sent": "",
        "error": None,
        "platform": "instagram",
    }

    try:
        # ── 1. Navigate to profile ────────────────────────────
        profile_url = f"{IG_BASE}/{username}/"
        await page.goto(profile_url, wait_until="load", timeout=45_000)
        # Wait for React to render profile buttons (Instagram SPA never reaches networkidle)
        try:
            await page.wait_for_selector(
                'button:has-text("Message"), button:has-text("Mensaje"), button:has-text("Follow"), button:has-text("Seguir")',
                timeout=10_000,
            )
        except Exception:
            pass  # Continue anyway — _first_visible will handle the not-found case
        await human_pause(2, 4)

        # ── 2. Simulate human scroll ──────────────────────────
        await page.evaluate("window.scrollBy(0, 220)")
        await human_pause(1.2, 2.5)
        await page.evaluate("window.scrollBy(0, -100)")
        await human_pause(0.5, 1.5)

        # ── 3. Click Message button ───────────────────────────
        msg_btn = await _first_visible(page, _MSG_BUTTON_SELECTORS)
        if not msg_btn:
            result["error"] = f"'Message' button not found on @{username} — account may be private or require follow"
            logger.warning(f"⚠️ {result['error']}")
            return result

        await msg_btn.click()
        await human_pause(1.5, 3)

        # Confirm DM panel opened (textbox present)
        textbox = await _first_visible(page, _TEXTBOX_SELECTORS)
        if not textbox:
            result["error"] = "DM panel did not open — textbox not found"
            logger.error(f"❌ {result['error']} (@{username})")
            return result

        # ── 4. Inject message via Lexical API ─────────────────
        # Step 4a — click textbox and type one char via Playwright keyboard
        # (creates the Lexical TextNode; execCommand inside evaluate lacks real focus)
        tb_locator = page.locator('div[contenteditable="true"][role="textbox"]').first
        await tb_locator.click()
        await human_pause(0.3, 0.6)
        await page.keyboard.type('x')
        await human_pause(0.6, 1.0)
        # Step 4b — overwrite with full message via Lexical internal API
        inject_result = await page.evaluate(_JS_SET_LEXICAL_TEXT, message)

        if not inject_result.get("ok"):
            result["error"] = f"Lexical injection failed: {inject_result.get('error')}"
            logger.error(f"❌ {result['error']} (@{username})")
            return result

        await human_pause(0.8, 1.5)

        # Brief wait for React to render the Send button after text injection
        await human_pause(0.4, 0.8)

        # ── 5. Send ───────────────────────────────────────────
        send_btn = await _first_visible(page, _SEND_BUTTON_SELECTORS)
        if send_btn:
            await send_btn.click()
        else:
            # Fallback: Enter key
            logger.debug(f"Send button not found for @{username}, using Enter key")
            await page.keyboard.press("Enter")

        await human_pause(2, 4)

        # ── 6. Verify ─────────────────────────────────────────
        verify = await page.evaluate(_JS_VERIFY_SENT)
        if verify.get("empty"):
            result["success"] = True
            result["message_sent"] = message
            logger.info(f"✉️  IG DM sent → @{username} ({len(message)} chars)")
        else:
            result["error"] = "Textbox not empty after send — message may not have been delivered"
            logger.warning(f"⚠️ {result['error']} (@{username})")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ IG DM error for @{username}: {e}")

    return result
