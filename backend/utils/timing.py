import time

from backend.settings import get_setting


def get_observation_delay_seconds() -> float:
    raw_value = get_setting(
        "automation",
        "observation_delay_seconds",
        default=0.0,
    )

    try:
        delay = float(raw_value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, delay)


def paced_sleep(base_seconds: float = 0.0, multiplier: float = 1.0) -> float:
    base = max(0.0, float(base_seconds or 0.0))
    extra = get_observation_delay_seconds() * max(0.0, float(multiplier or 0.0))
    total = base + extra

    if total > 0:
        time.sleep(total)

    return total


def observation_pause(multiplier: float = 1.0) -> float:
    return paced_sleep(0.0, multiplier=multiplier)
