import json
import os
from copy import deepcopy
from pathlib import Path


DEFAULT_SETTINGS = {
    "app": {
        "name": "EMBASA",
        "version": "2026.04.14",
        "company_code": "EMBA",
    },
    "security": {
        "mask_documents_in_logs": True,
    },
    "cache": {
        "enabled": True,
        "persist_to_disk": True,
        "ttl_days": 30,
        "max_entries": 2000,
        "file_name": "cliente_cache.json",
    },
    "automation": {
        "observation_delay_seconds": 2.0,
    },
}


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_runtime_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")

    if local_appdata:
        root = Path(local_appdata) / "EMBASA"
    else:
        root = Path.home() / ".embasa"

    root.mkdir(parents=True, exist_ok=True)
    return root


def _deep_merge(base: dict, override: dict) -> dict:
    merged = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def _candidate_override_paths() -> list[Path]:
    return [
        get_project_root() / "embasa_settings.json",
        get_runtime_root() / "embasa_settings.json",
    ]


def load_settings() -> dict:
    settings = deepcopy(DEFAULT_SETTINGS)
    loaded_from = []

    for path in _candidate_override_paths():
        if not path.exists():
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        settings = _deep_merge(settings, payload)
        loaded_from.append(str(path))

    settings["_meta"] = {
        "project_root": str(get_project_root()),
        "runtime_root": str(get_runtime_root()),
        "loaded_from": loaded_from,
    }

    return settings


SETTINGS = load_settings()


def get_setting(*keys, default=None):
    current = SETTINGS

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]

    return current
