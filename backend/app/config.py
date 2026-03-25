"""Application configuration via environment variables and .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    app_name: str = "StudioLink Outreach Engine"
    debug: bool = True

    # ── Database ─────────────────────────────────────────────
    database_url: str = "sqlite:///./studiolink.db"

    # ── Browser / Playwright ─────────────────────────────────
    chrome_profile_path: str = str(
        Path.home() / "Library/Application Support/Google/Chrome/Default"
    )
    headless: bool = False  # NEVER headless in production

    # ── TikTok Safety Limits ─────────────────────────────────
    min_delay_between_dms_sec: int = 900   # 15 min
    max_delay_between_dms_sec: int = 1200  # 20 min
    max_dms_per_day: int = 45
    min_action_delay_sec: float = 45.0
    max_action_delay_sec: float = 90.0

    # ── Keystroke Dynamics ───────────────────────────────────
    min_keystroke_delay_ms: int = 50
    max_keystroke_delay_ms: int = 180

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
