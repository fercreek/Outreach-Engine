"""
One-time Instagram login script.

Run this ONCE to save your Instagram session to the dedicated Playwright profile.
After login, close the browser window — the session cookie is saved automatically.

Usage:
    cd backend
    source .venv/bin/activate
    python login_ig.py
"""

import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE_DIR = Path.home() / ".outreach-engine" / "profile-v2"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run():
    async with async_playwright() as pw:
        logger.info("Opening Chrome with dedicated profile...")
        context = await pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = await context.new_page()
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")

        logger.info("=" * 55)
        logger.info("  Log in to @studiolink.online in the Chrome window.")
        logger.info("  Once you see your feed, come back here and")
        logger.info("  press Ctrl+C to close and save the session.")
        logger.info("=" * 55)

        # Poll until logged in, then auto-close
        while True:
            await asyncio.sleep(5)
            try:
                logged_in = await page.evaluate("document.cookie.includes('ds_user_id')")
            except Exception:
                continue
            if logged_in:
                logger.info("✅ Session detected! Closing in 5s...")
                await asyncio.sleep(5)
                break

        await context.close()
        logger.info("✅ Session saved. Run test_ig_outreach.py now.")


if __name__ == "__main__":
    asyncio.run(run())
