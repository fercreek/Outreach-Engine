"""Warming service — visit profiles, watch videos, leave tactical likes."""

import logging
import random

from playwright.async_api import Page

from app.services.browser import get_browser_page
from app.utils.jitter import human_pause

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"


async def warm_profile(username: str) -> dict:
    """
    Execute the warming sequence for a lead:
    1. Visit their profile
    2. Scroll through their feed
    3. Watch 1-2 videos briefly
    4. Leave 1 tactical like

    This generates a friendly notification before the DM.
    """
    page = await get_browser_page()
    url = f"{TIKTOK_BASE}/@{username}"
    result = {"username": username, "visited": False, "videos_watched": 0, "liked": False}

    try:
        # ── Step 1: Visit Profile ────────────────────────────
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await human_pause(3, 7)  # Linger on profile like a real person
        result["visited"] = True
        logger.info(f"👁️ Visited @{username}'s profile")

        # ── Step 2: Scroll Feed ──────────────────────────────
        scroll_count = random.randint(2, 4)
        for _ in range(scroll_count):
            await page.mouse.wheel(0, random.randint(300, 600))
            await human_pause(1.5, 3.5)

        # ── Step 3: Watch Videos ─────────────────────────────
        video_links = await page.locator('[data-e2e="user-post-item"] a').all()
        videos_to_watch = min(random.randint(1, 2), len(video_links))

        for i in range(videos_to_watch):
            try:
                await video_links[i].click()
                await human_pause(5, 15)  # Watch for 5-15 seconds
                result["videos_watched"] += 1
                logger.info(f"🎬 Watched video {i+1} from @{username}")

                # ── Step 4: Like (only on the first video) ───
                if i == 0 and not result["liked"]:
                    like_btn = page.locator('[data-e2e="like-icon"]').first
                    if await like_btn.count() > 0:
                        # Check if not already liked
                        aria_label = await like_btn.get_attribute("aria-label") or ""
                        if "like" in aria_label.lower() and "unlike" not in aria_label.lower():
                            await like_btn.click()
                            result["liked"] = True
                            logger.info(f"❤️ Liked @{username}'s video")
                            await human_pause(1, 3)

                # Go back to profile
                await page.go_back(wait_until="networkidle", timeout=15000)
                await human_pause(2, 4)

            except Exception as video_err:
                logger.warning(f"⚠️ Video interaction error: {video_err}")
                # Try to navigate back to profile
                await page.goto(url, wait_until="networkidle", timeout=15000)
                await human_pause(2, 4)

        logger.info(
            f"✅ Warming complete for @{username}: "
            f"visited={result['visited']}, videos={result['videos_watched']}, liked={result['liked']}"
        )

    except Exception as e:
        logger.error(f"❌ Warming error for @{username}: {e}")

    return result
