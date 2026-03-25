"""Playwright browser manager — persistent Chrome context with stealth."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from app.config import settings

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Singleton manager for Playwright browser with persistent profile.
    Uses the real Chrome user data dir to maintain cookies & sessions.
    """

    _instance: Optional["BrowserManager"] = None
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None

    @classmethod
    async def get_instance(cls) -> "BrowserManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def launch(self) -> Page:
        """Launch browser with persistent context (non-headless)."""
        if self._page and not self._page.is_closed():
            return self._page

        self._playwright = await async_playwright().start()

        # Use persistent context for cookie/session persistence
        user_data_dir = Path(settings.chrome_profile_path).parent
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=settings.headless,
            viewport={"width": 1280, "height": 900},
            locale="es-MX",
            timezone_id="America/Monterrey",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
            ],
        )

        # Apply stealth tweaks
        await self._apply_stealth(self._context)

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        logger.info("🟢 Browser launched with persistent context")
        return self._page

    async def get_page(self) -> Page:
        """Get or create the active page."""
        if self._page is None or self._page.is_closed():
            return await self.launch()
        return self._page

    async def close(self):
        """Clean shutdown."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._playwright = None
        logger.info("🔴 Browser closed")

    async def _apply_stealth(self, context: BrowserContext):
        """
        Inject stealth scripts to evade bot detection.
        Patches navigator.webdriver, plugins, languages, etc.
        """
        stealth_js = """
        () => {
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Fake plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Fake languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-MX', 'es', 'en-US', 'en'],
            });

            // Patch chrome runtime
            window.chrome = { runtime: {} };

            // Patch permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters);
        }
        """
        await context.add_init_script(stealth_js)


# Global convenience function
async def get_browser_page() -> Page:
    manager = await BrowserManager.get_instance()
    return await manager.get_page()
