"""Application configuration via environment variables and .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    app_name: str = "StudioLink Outreach Engine"
    debug: bool = True

    # ── Database ─────────────────────────────────────────────
    database_url: str = "sqlite:///./studiolink_v2.db"

    chrome_profile_path: str = str(
        Path.home() / ".outreach-engine/profile-v2"
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

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-haiku-20241022"

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str | None = None
    escalation_whatsapp_to: str | None = None

    agent_auto_on_reply: bool = True
    trial_signup_url: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
