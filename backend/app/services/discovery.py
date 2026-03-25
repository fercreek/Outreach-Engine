"""Discovery service — scrape TikTok profiles from hashtags and following lists."""

import logging
import re
from typing import Optional

from playwright.async_api import Page

from app.services.browser import get_browser_page
from app.utils.jitter import human_pause

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"


async def discover_from_following(
    source_username: str = "studio.link1",
    max_profiles: int = 50,
) -> list[dict]:
    """
    Scrape profiles from a user's 'Following' list on TikTok.
    Returns list of {username, profile_url}.
    """
    page = await get_browser_page()
    url = f"{TIKTOK_BASE}/@{source_username}"
    results: list[dict] = []

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await human_pause(3, 6)

        # Click on "Following" count to open the list
        following_link = page.locator('[data-e2e="following-count"]')
        if await following_link.count() > 0:
            await following_link.click()
            await human_pause(2, 4)

            # Scroll and collect user links
            for _ in range(max_profiles // 10):
                user_links = await page.locator(
                    '[data-e2e="following-item"] a[href*="/@"]'
                ).all()

                for link in user_links:
                    href = await link.get_attribute("href")
                    if href and "/@" in href:
                        username = href.split("/@")[-1].split("?")[0]
                        if username and username not in [r["username"] for r in results]:
                            results.append({
                                "username": username,
                                "profile_url": f"{TIKTOK_BASE}/@{username}",
                            })

                    if len(results) >= max_profiles:
                        break

                if len(results) >= max_profiles:
                    break

                # Scroll down for more
                await page.mouse.wheel(0, 800)
                await human_pause(1.5, 3)

        logger.info(f"📋 Discovered {len(results)} profiles from @{source_username}'s following")

    except Exception as e:
        logger.error(f"❌ Discovery error: {e}")

    return results


async def discover_from_hashtag(
    hashtag: str,
    max_profiles: int = 30,
) -> list[dict]:
    """
    Scrape creator profiles from a TikTok hashtag page.
    Returns list of {username, profile_url}.
    """
    page = await get_browser_page()
    tag = hashtag.lstrip("#")
    url = f"{TIKTOK_BASE}/tag/{tag}"
    results: list[dict] = []

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await human_pause(3, 6)

        # Collect unique creator links from video cards
        for _ in range(max_profiles // 5):
            author_links = await page.locator('a[href*="/@"]').all()

            for link in author_links:
                href = await link.get_attribute("href")
                if href and "/@" in href:
                    username = href.split("/@")[-1].split("?")[0].split("/")[0]
                    if username and username not in [r["username"] for r in results]:
                        results.append({
                            "username": username,
                            "profile_url": f"{TIKTOK_BASE}/@{username}",
                        })

                if len(results) >= max_profiles:
                    break

            if len(results) >= max_profiles:
                break

            await page.mouse.wheel(0, 600)
            await human_pause(2, 4)

        logger.info(f"📋 Discovered {len(results)} profiles from #{tag}")

    except Exception as e:
        logger.error(f"❌ Hashtag discovery error: {e}")

    return results


async def extract_profile_info(username: str) -> dict:
    """
    Visit a TikTok profile and extract bio, follower count, etc.
    Used during the Qualification step.
    """
    page = await get_browser_page()
    url = f"{TIKTOK_BASE}/@{username}"
    info: dict = {"username": username, "profile_url": url}

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await human_pause(2, 5)

        # Bio
        bio_el = page.locator('[data-e2e="user-bio"]')
        if await bio_el.count() > 0:
            info["bio"] = await bio_el.inner_text()

        # Follower count
        follower_el = page.locator('[data-e2e="followers-count"]')
        if await follower_el.count() > 0:
            raw = await follower_el.inner_text()
            info["follower_count"] = _parse_count(raw)

        # Display name (potential business name)
        name_el = page.locator('[data-e2e="user-title"]')
        if await name_el.count() > 0:
            info["business_name"] = await name_el.inner_text()

        logger.info(f"📄 Extracted profile info for @{username}")

    except Exception as e:
        logger.error(f"❌ Profile extraction error for @{username}: {e}")

    return info


def _parse_count(raw: str) -> int:
    """Parse TikTok shorthand numbers like '12.3K' → 12300."""
    raw = raw.strip().upper().replace(",", "")
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if raw.endswith(suffix):
            try:
                return int(float(raw[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(raw)
    except ValueError:
        return 0
