import json
import os
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


# Configuracao padrao do sistema; pode ser sobrescrita por embasa_settings.json.
DEFAULT_SETTINGS = {
    "app": {
        "name": "EMBASA",
        "version": "1.4.4",
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
        "shared_dir": "",
        "fallback_to_local": True,
        "reload_on_read": True,
        "lock_timeout_seconds": 3,
    },
    "history": {
        "enabled": True,
        "shared_dir": "dados_compartilhados/historico",
        "db_file": "historico_pedidos.json",
        "max_entries": 5000,
        "max_results": 200,
        "fallback_to_local": True,
        "lock_timeout_seconds": 5,
    },
    "startup": {
        "require_sap_session": True,
    },
    "timing": {
        "action_delay_seconds": 0,
        "max_action_delay_seconds": 30,
    },
    "support": {
        "notification_email_enabled": False,
        "destination_email": "",
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_username": "",
        "smtp_password": "",
        "smtp_from_email": "",
        "smtp_from_name": "EMBASA API",
        "subject_prefix": "[EMBASA Atendimento]",
    },
}


# Raiz do projeto no codigo fonte ou pasta do .exe quando empacotado.
@lru_cache(maxsize=1)
def get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


# Pasta local por usuário para cache, logs e configurações em runtime.
@lru_cache(maxsize=1)
def get_runtime_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")

    if local_appdata:
        root = Path(local_appdata) / "EMBASA"
    else:
        root = Path.home() / ".embasa"

    root.mkdir(parents=True, exist_ok=True)
    return root


# Mescla configuracoes mantendo defaults quando o JSON sobrescreve apenas parte.
def _deep_merge(base: dict, override: dict) -> dict:
    merged = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


# Locais aceitos para o arquivo embasa_settings.json.
def _candidate_override_paths() -> list[Path]:
    return [
        get_project_root() / "embasa_settings.json",
        get_runtime_root() / "embasa_settings.json",
    ]


# Carrega settings finais: defaults + sobrescritas locais/de rede.
def load_settings() -> dict:
    settings = deepcopy(DEFAULT_SETTINGS)
    loaded_from = []

    for path in _candidate_override_paths():
        if not path.exists():
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
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


# Busca uma chave aninhada de configuracao com fallback seguro.
def get_setting(*keys, default=None):
    current = SETTINGS

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]

    return current
