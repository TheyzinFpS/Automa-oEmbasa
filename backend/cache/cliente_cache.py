import json
from datetime import datetime, timedelta
from pathlib import Path

from backend.settings import get_runtime_root, get_setting


# Cache local de clientes por CPF/CNPJ para evitar busca repetida no XD03.
class ClienteCache:
    def __init__(self, cache_path: str | None = None):
        self.enabled = bool(get_setting("cache", "enabled", default=True))
        self.persist_to_disk = bool(get_setting("cache", "persist_to_disk", default=True))
        self.ttl_days = int(get_setting("cache", "ttl_days", default=30))
        self.max_entries = int(get_setting("cache", "max_entries", default=2000))

        default_path = get_runtime_root() / "cache" / get_setting(
            "cache",
            "file_name",
            default="cliente_cache.json",
        )

        self.cache_path = Path(cache_path) if cache_path else default_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        self.cache = {}
        self._load()
        self._purge_expired()

    # Carrega o cache salvo no disco, quando habilitado.
    def _load(self):
        if not self.enabled or not self.persist_to_disk or not self.cache_path.exists():
            return

        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            self.cache = {}
            return

        if isinstance(payload, dict):
            self.cache = payload
        else:
            self.cache = {}

    # Salva o cache de forma atomica para reduzir risco de arquivo corrompido.
    def _save(self):
        if not self.enabled or not self.persist_to_disk:
            return

        try:
            temp_path = self.cache_path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self.cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.cache_path)
        except Exception:
            # Cache local não deve derrubar o fluxo principal.
            return

    # Verifica se um registro passou do prazo de validade.
    def _is_expired(self, registro: dict) -> bool:
        timestamp = str(registro.get("timestamp", "")).strip()

        if not timestamp:
            return True

        try:
            created_at = datetime.fromisoformat(timestamp)
        except ValueError:
            return True

        return created_at < datetime.now() - timedelta(days=self.ttl_days)

    # Remove registros vencidos e limita o tamanho total do cache.
    def _purge_expired(self, save_changes=True):
        if not self.cache:
            return False

        ativos = {
            documento: dados
            for documento, dados in self.cache.items()
            if isinstance(dados, dict) and not self._is_expired(dados)
        }

        if len(ativos) > self.max_entries:
            ordenados = sorted(
                ativos.items(),
                key=lambda item: item[1].get("timestamp", ""),
                reverse=True,
            )
            ativos = dict(ordenados[: self.max_entries])

        changed = ativos != self.cache

        if changed:
            self.cache = ativos
            if save_changes:
                self._save()

        return changed

    # Busca um cliente no cache e invalida automaticamente dados vencidos.
    def get(self, documento):
        if not self.enabled:
            return None

        registro = self.cache.get(documento)

        if not registro:
            return None

        if self._is_expired(registro):
            self.cache.pop(documento, None)
            self._save()
            return None

        return registro

    # Grava cliente retornado pelo SAP para reuso em proximas execucoes.
    def set(self, documento, dados):
        if not self.enabled:
            return

        registro = {
            "cliente": dados["cliente"],
            "tipo_documento": dados["tipo_documento"],
            "documento": documento,
            "nome_cliente": dados.get("nome_cliente"),
            "setores_atividade": dados.get("setores_atividade") or [],
            "tipos_suportados": dados.get("tipos_suportados") or [],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        changed = self.cache.get(documento) != registro
        self.cache[documento] = registro
        purged = self._purge_expired(save_changes=False)

        if changed or purged:
            self._save()

    def exists(self, documento):
        return self.get(documento) is not None

    # Limpa todo o cache local.
    def clear(self):
        if not self.cache:
            return

        self.cache = {}
        self._save()

    # Retorna informacoes de diagnostico do cache para a API/interface.
    def stats(self):
        return {
            "enabled": self.enabled,
            "persist_to_disk": self.persist_to_disk,
            "ttl_days": self.ttl_days,
            "total": len(self.cache),
            "cache_path": str(self.cache_path),
        }
