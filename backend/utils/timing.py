import time

from backend.settings import get_setting


# Lê o atraso artificial usado apenas para demonstração/acompanhamento visual.
def get_action_delay_seconds() -> float:
    try:
        delay = float(get_setting("timing", "action_delay_seconds", default=0) or 0)
    except (TypeError, ValueError):
        delay = 0.0

    try:
        max_delay = float(
            get_setting("timing", "max_action_delay_seconds", default=30) or 30
        )
    except (TypeError, ValueError):
        max_delay = 30.0

    return max(0.0, min(delay, max_delay))


# Pausa controlada por embasa_settings.json, sem espalhar time.sleep pelo projeto.
def paced_sleep(base_seconds: float = 0.0, multiplier: float = 1.0) -> float:
    delay = max(float(base_seconds or 0.0), get_action_delay_seconds())
    delay = max(0.0, delay * max(0.0, float(multiplier or 1.0)))

    if delay > 0:
        time.sleep(delay)

    return delay


# Nome semântico para pausas de demonstração/observação.
def observation_pause(multiplier: float = 1.0) -> float:
    return paced_sleep(0.0, multiplier=multiplier)
