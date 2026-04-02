"""
Test script — Instagram DM outreach via Playwright + Lexical injection.

Usage:
    cd backend
    source .venv/bin/activate
    python test_ig_outreach.py

Prerequisites:
    - Chrome running with remote debugging:
        open -a "Google Chrome" --args --remote-debugging-port=9222
          --user-data-dir=$HOME/.outreach-engine/chrome-debug
    - Active Instagram session in that Chrome instance
    - OR: set USE_PERSISTENT_PROFILE=True to use the saved Playwright profile

Results are logged to console and saved to test_ig_results.json.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

# ── Config ────────────────────────────────────────────────────────────────────

# Connect to existing Chrome with active IG session
CHROME_CDP_URL = "http://localhost:9222"

# Alternatively, use Playwright's own persistent profile (set to True)
USE_PERSISTENT_PROFILE = True
PROFILE_DIR = Path.home() / ".outreach-engine" / "profile-v2"

# Handles to DM (adjust as needed)
HANDLES = [
    "soystardancemx",
    "vayla.dance",
    "bembe.oficial",
    "mambolee.vialaluz",
    "danzieladancestudiovs",
    "academiadebailejf",
    "palarumba_academia",
    "danzayaacademiadebaile",
]

MESSAGE = (
    "Hola!!! como programador y bailarin🕺 uso tecnología para automatizar el lado "
    "aburrido de dar clases: pagos, reservas, seguimiento de alumnos.. Tu perfil me "
    "dio curiosidad por cómo lo llevan ahorita... Te gustaria automatizar tus "
    "procesos? Aquí para ayudar 🙂"
)

# Delays between DMs (seconds) — keep human-like
MIN_DELAY = 25
MAX_DELAY = 40

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Minimal Lead stub (avoids importing the full app) ────────────────────────
class LeadStub:
    def __init__(self, username: str):
        self.username = username


# ── Main ──────────────────────────────────────────────────────────────────────

async def run():
    from app.services.outreach_ig import send_dm_instagram

    results = []
    start_time = time.time()

    async with async_playwright() as pw:
        if USE_PERSISTENT_PROFILE:
            browser = await pw.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                args=["--start-maximized"],
            )
            page = await browser.new_page()
        else:
            # Connect to already-running Chrome (session already logged in)
            browser = await pw.chromium.connect_over_cdp(CHROME_CDP_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

        # ── Verify Instagram session ──────────────────────────
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=20_000)
        await asyncio.sleep(3)
        logged_in = await page.evaluate("document.cookie.includes('ds_user_id')")
        if not logged_in:
            logger.error("❌ No Instagram session in profile.")
            logger.error("   Run this first to save your session:")
            logger.error("   python login_ig.py")
            logger.error("   Then re-run this script.")
            return

        logger.info(f"🚀 Starting IG outreach — {len(HANDLES)} handles")
        logger.info(f"   Message length: {len(MESSAGE)} chars")
        logger.info(f"   Delay range: {MIN_DELAY}–{MAX_DELAY}s between DMs")
        logger.info("─" * 60)

        for i, handle in enumerate(HANDLES, 1):
            lead = LeadStub(handle)
            logger.info(f"[{i}/{len(HANDLES)}] @{handle}")

            result = await send_dm_instagram(page, lead, MESSAGE)
            result["index"] = i
            result["timestamp"] = datetime.now().isoformat()
            results.append(result)

            status = "✅ SENT" if result["success"] else f"❌ FAILED — {result.get('error')}"
            logger.info(f"    {status}")

            # Delay before next (skip after last)
            if i < len(HANDLES):
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                logger.info(f"    ⏳ Waiting {delay:.0f}s before next...")
                await asyncio.sleep(delay)

        # ── Summary ───────────────────────────────────────────
        elapsed = time.time() - start_time
        sent = sum(1 for r in results if r["success"])
        failed = len(results) - sent

        logger.info("─" * 60)
        logger.info(f"📊 REPORT")
        logger.info(f"   Sent:    {sent}/{len(HANDLES)}")
        logger.info(f"   Failed:  {failed}/{len(HANDLES)}")
        logger.info(f"   Elapsed: {elapsed/60:.1f} min")
        logger.info(f"   Avg/DM:  {elapsed/len(HANDLES)/60:.1f} min")

        for r in results:
            icon = "✅" if r["success"] else "❌"
            err = f" — {r['error']}" if not r["success"] else ""
            logger.info(f"   {icon} [{r['index']:02d}] @{r['username']}{err}")

        # Save results
        out_path = Path(__file__).parent / "test_ig_results.json"
        with open(out_path, "w") as f:
            json.dump(
                {
                    "run_at": datetime.now().isoformat(),
                    "total": len(HANDLES),
                    "sent": sent,
                    "failed": failed,
                    "elapsed_sec": round(elapsed, 1),
                    "results": results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        logger.info(f"   Results saved → {out_path}")

        # Don't close browser when connected via CDP — it's an existing Chrome instance.
        # Closing would kill the user's browser session.
        if USE_PERSISTENT_PROFILE:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
