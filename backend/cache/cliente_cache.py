import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from backend.settings import get_project_root, get_runtime_root, get_setting


# Cache de clientes por CPF/CNPJ para evitar buscas repetidas no XD03.
class ClienteCache:
    def __init__(self, cache_path: str | None = None):
        self.enabled = bool(get_setting("cache", "enabled", default=True))
        self.persist_to_disk = bool(get_setting("cache", "persist_to_disk", default=True))
        self.ttl_days = int(get_setting("cache", "ttl_days", default=30))
        self.max_entries = int(get_setting("cache", "max_entries", default=2000))
        self.file_name = str(get_setting("cache", "file_name", default="cliente_cache.json"))
        self.fallback_to_local = bool(get_setting("cache", "fallback_to_local", default=True))
        self.reload_on_read = bool(get_setting("cache", "reload_on_read", default=True))
        self.lock_timeout_seconds = float(
            get_setting("cache", "lock_timeout_seconds", default=3)
        )

        self.local_cache_path = get_runtime_root() / "cache" / self.file_name
        self.shared_dir = self._resolve_shared_dir()
        self.storage_mode = "local"
        self.cache_path = self._select_cache_path(cache_path)
        self.lock_path = self.cache_path.with_suffix(".lock")

        self.cache = {}
        self._load()
        self._bootstrap_shared_cache_from_local()
        self._purge_expired()

    # Resolve caminho absoluto da pasta compartilhada configurada.
    def _resolve_shared_dir(self):
        configured = str(get_setting("cache", "shared_dir", default="") or "").strip()

        if not configured:
            return None

        expanded = os.path.expandvars(os.path.expanduser(configured))
        path = Path(expanded)

        if not path.is_absolute():
            # Quando o app é aberto pela rede, main.py copia o onedir para
            # LOCALAPPDATA e informa a origem real em EMBASA_NETWORK_SOURCE.
            # Assim o cache relativo continua ficando na pasta compartilhada.
            base_dir = Path(os.environ.get("EMBASA_NETWORK_SOURCE") or get_project_root())
            path = base_dir / path

        return path

    # Garante que a pasta de cache existe e aceita escrita.
    def _storage_available(self, cache_path: Path) -> bool:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            probe = cache_path.parent / ".embasa_cache_write_test.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    # Seleciona cache compartilhado quando possivel; caso contrario usa fallback local.
    def _select_cache_path(self, explicit_cache_path: str | None) -> Path:
        if explicit_cache_path:
            path = Path(explicit_cache_path)
            self.storage_mode = "custom"
            self._storage_available(path)
            return path

        if self.shared_dir:
            shared_cache_path = self.shared_dir / self.file_name

            if self._storage_available(shared_cache_path):
                self.storage_mode = "shared"
                return shared_cache_path

            if not self.fallback_to_local:
                self.storage_mode = "shared_unavailable"
                return shared_cache_path

        self._storage_available(self.local_cache_path)
        self.storage_mode = "local"
        return self.local_cache_path

    # Lê o arquivo JSON do disco sem derrubar o fluxo caso esteja vazio/corrompido.
    def _read_disk_cache(self) -> dict:
        if not self.persist_to_disk or not self.cache_path.exists():
            return {}

        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

        return payload if isinstance(payload, dict) else {}

    # Grava o JSON de forma atomica; cada processo usa arquivo temporario proprio.
    def _write_disk_cache(self, payload: dict):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.cache_path.with_name(
            f"{self.cache_path.name}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
        )

        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temp_path, self.cache_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    # Cria lock simples por arquivo para reduzir conflito entre usuarios na rede.
    def _acquire_lock(self):
        deadline = time.monotonic() + max(0.2, self.lock_timeout_seconds)

        while time.monotonic() < deadline:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                payload = f"{os.getpid()}|{datetime.now().isoformat(timespec='seconds')}"
                os.write(fd, payload.encode("utf-8", errors="ignore"))
                return fd
            except FileExistsError:
                self._remove_stale_lock()
                time.sleep(0.05)
            except Exception:
                return None

        return None

    # Remove lock antigo deixado por fechamento inesperado do app.
    def _remove_stale_lock(self):
        try:
            age_seconds = time.time() - self.lock_path.stat().st_mtime
        except Exception:
            return

        if age_seconds < max(10, self.lock_timeout_seconds * 4):
            return

        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    def _release_lock(self, fd):
        try:
            os.close(fd)
        except Exception:
            pass

        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    @contextmanager
    def _file_lock(self):
        fd = self._acquire_lock()

        try:
            yield fd is not None
        finally:
            if fd is not None:
                self._release_lock(fd)

    # Carrega o cache salvo no disco, quando habilitado.
    def _load(self):
        if not self.enabled or not self.persist_to_disk:
            return

        self.cache = self._read_disk_cache()

    # Salva o cache sem deixar falha de disco derrubar a automacao principal.
    def _save(self):
        if not self.enabled or not self.persist_to_disk:
            return

        try:
            with self._file_lock() as locked:
                if self.storage_mode.startswith("shared") and not locked:
                    return
                self._write_disk_cache(self.cache)
        except Exception:
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

    # Converte timestamp do registro para comparar qual dado e mais recente.
    def _timestamp_for_compare(self, registro: dict):
        try:
            return datetime.fromisoformat(str(registro.get("timestamp", "")).strip())
        except Exception:
            return datetime.min

    # Aproveita cache local antigo e envia para o cache compartilhado uma unica vez.
    def _bootstrap_shared_cache_from_local(self):
        if self.storage_mode != "shared":
            return

        if self.local_cache_path == self.cache_path or not self.local_cache_path.exists():
            return

        try:
            local_payload = json.loads(
                self.local_cache_path.read_text(encoding="utf-8-sig")
            )
        except Exception:
            return

        if not isinstance(local_payload, dict) or not local_payload:
            return

        changed = False

        for documento, local_registro in local_payload.items():
            if not isinstance(local_registro, dict) or self._is_expired(local_registro):
                continue

            atual = self.cache.get(documento)

            if not atual or self._timestamp_for_compare(
                local_registro
            ) > self._timestamp_for_compare(atual):
                self.cache[documento] = local_registro
                changed = True

        if changed:
            self._save()

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

    # Busca um cliente no cache e recarrega o arquivo para ver dados de outros usuarios.
    def get(self, documento):
        if not self.enabled:
            return None

        if self.persist_to_disk and self.reload_on_read:
            self._load()

        registro = self.cache.get(documento)

        if not registro:
            return None

        if self._is_expired(registro):
            self.cache.pop(documento, None)
            self._save()
            return None

        return registro

    # Grava cliente retornado pelo SAP para reuso por todos os usuarios do setor.
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

        if not self.persist_to_disk:
            self.cache[documento] = registro
            self._purge_expired(save_changes=False)
            return

        try:
            with self._file_lock() as locked:
                if self.storage_mode.startswith("shared") and not locked:
                    return

                self.cache = self._read_disk_cache()
                changed = self.cache.get(documento) != registro
                self.cache[documento] = registro
                purged = self._purge_expired(save_changes=False)

                if changed or purged:
                    self._write_disk_cache(self.cache)
        except Exception:
            return

    def exists(self, documento):
        return self.get(documento) is not None

    # Limpa todo o cache ativo.
    def clear(self):
        if not self.cache:
            return

        self.cache = {}
        self._save()

    # Retorna informacoes de diagnostico do cache para a API/interface.
    def stats(self):
        if self.enabled and self.persist_to_disk and self.reload_on_read:
            self._load()

        return {
            "enabled": self.enabled,
            "persist_to_disk": self.persist_to_disk,
            "ttl_days": self.ttl_days,
            "total": len(self.cache),
            "storage_mode": self.storage_mode,
            "shared_dir": str(self.shared_dir) if self.shared_dir else "",
            "cache_path": str(self.cache_path),
            "local_cache_path": str(self.local_cache_path),
        }
