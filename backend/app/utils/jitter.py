"""Gaussian jitter and human-like delay utilities."""

import asyncio
import random
import numpy as np

from app.config import settings


def gaussian_delay(min_sec: float, max_sec: float) -> float:
    """
    Generate a delay following a truncated Gaussian distribution.
    The mean is the midpoint and sigma is designed so ~95% of values
    fall within [min_sec, max_sec].
    """
    mean = (min_sec + max_sec) / 2
    sigma = (max_sec - min_sec) / 4  # 2σ covers ~95%
    delay = np.random.normal(mean, sigma)
    return float(np.clip(delay, min_sec, max_sec))


async def human_pause(min_sec: float | None = None, max_sec: float | None = None) -> float:
    """Sleep for a human-like Gaussian-distributed duration. Returns actual delay."""
    _min = min_sec or settings.min_action_delay_sec
    _max = max_sec or settings.max_action_delay_sec
    delay = gaussian_delay(_min, _max)
    await asyncio.sleep(delay)
    return delay


async def dm_cooldown() -> float:
    """Sleep between DM sends (15-20 min with Gaussian jitter)."""
    return await human_pause(
        settings.min_delay_between_dms_sec,
        settings.max_delay_between_dms_sec,
    )


def keystroke_delay_ms() -> int:
    """Random per-key delay for realistic typing simulation."""
    return random.randint(
        settings.min_keystroke_delay_ms,
        settings.max_keystroke_delay_ms,
    )
