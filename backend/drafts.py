import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.settings import get_project_root, get_runtime_root, get_setting


def _agora() -> datetime:
    return datetime.now()


def _texto(valor: Any, fallback: str = "") -> str:
    texto = str(valor or "").strip()
    return texto or fallback


def _resolver_caminho_configurado(valor: str, fallback: Path) -> Path:
    caminho = Path(str(valor or "").strip()) if valor else fallback

    if not caminho.is_absolute():
        caminho = get_project_root() / caminho

    return caminho


def _drafts_root() -> Path:
    configurado = get_setting("drafts", "shared_dir", default="")
    fallback = get_runtime_root() / "rascunhos"
    root = _resolver_caminho_configurado(configurado, fallback)

    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except Exception:
        if get_setting("drafts", "fallback_to_local", default=True):
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        raise


def _db_path() -> Path:
    file_name = get_setting("drafts", "client_db_file", default="rascunhos_clientes.json")
    return _drafts_root() / str(file_name or "rascunhos_clientes.json")


@contextmanager
def _file_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    timeout = float(get_setting("drafts", "lock_timeout_seconds", default=5) or 5)
    start = time.monotonic()
    fd = None

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode("ascii", errors="ignore"))
            break
        except FileExistsError:
            if time.monotonic() - start > timeout:
                try:
                    lock_path.unlink()
                except Exception:
                    pass
            time.sleep(0.08)

    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        try:
            lock_path.unlink()
        except Exception:
            pass


def _normalizar_documento(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))[:14]


def _normalizar_rascunho(payload: dict[str, Any]) -> dict[str, Any]:
    agora = _agora().isoformat(timespec="seconds")
    doc = _normalizar_documento(payload.get("doc") or payload.get("documento"))
    enderecos = payload.get("enderecos") if isinstance(payload.get("enderecos"), list) else []
    draft_id = _texto(payload.get("id"))

    if not draft_id:
        sufixo_doc = doc[-6:] if doc else uuid.uuid4().hex[:6]
        draft_id = f"rascunho_{_agora().strftime('%Y%m%d%H%M%S')}_{sufixo_doc}_{uuid.uuid4().hex[:6]}"

    return {
        "id": draft_id,
        "doc": doc,
        "doc_formatado": _texto(payload.get("doc_formatado") or payload.get("documento_formatado")),
        "tipo": _texto(payload.get("tipo")),
        "tipo_label": _texto(payload.get("tipo_label")),
        "valor": _texto(payload.get("valor")),
        "modo_valor": _texto(payload.get("modo_valor"), "auto"),
        "enderecos": enderecos,
        "observacao": _texto(payload.get("observacao")),
        "status": "rascunho",
        "criado_em": _texto(payload.get("criado_em"), agora),
        "atualizado_em": agora,
    }


def _ler_banco() -> list[dict[str, Any]]:
    path = _db_path()

    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []

    if isinstance(payload, dict):
        itens = payload.get("rascunhos")
        return itens if isinstance(itens, list) else []

    return payload if isinstance(payload, list) else []


def _salvar_banco(rascunhos: list[dict[str, Any]]) -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "schema": 1,
        "atualizado_em": _agora().isoformat(timespec="seconds"),
        "rascunhos": rascunhos,
    }
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def listar_rascunhos_clientes(filtro: str = "", limite: int | None = None) -> list[dict[str, Any]]:
    rascunhos = _ler_banco()
    termo = _texto(filtro).casefold()

    if termo:
        def combina(item: dict[str, Any]) -> bool:
            valores = [
                item.get("doc"),
                item.get("doc_formatado"),
                item.get("tipo"),
                item.get("tipo_label"),
                item.get("valor"),
            ]

            for endereco in item.get("enderecos") or []:
                if isinstance(endereco, dict):
                    valores.extend(
                        [
                            endereco.get("empreendimento"),
                            endereco.get("rua"),
                            endereco.get("bairro"),
                            endereco.get("cidade"),
                            endereco.get("cep"),
                        ]
                    )

            return termo in " ".join(str(valor or "") for valor in valores).casefold()

        rascunhos = [item for item in rascunhos if combina(item)]

    rascunhos.sort(key=lambda item: str(item.get("atualizado_em") or ""), reverse=True)
    limite_final = limite or int(get_setting("drafts", "max_results", default=100) or 100)
    return rascunhos[:limite_final]


def salvar_rascunho_cliente(payload: dict[str, Any]) -> dict[str, Any]:
    rascunho = _normalizar_rascunho(payload if isinstance(payload, dict) else {})
    max_entries = int(get_setting("drafts", "max_entries", default=500) or 500)
    path = _db_path()

    with _file_lock(path):
        rascunhos = _ler_banco()
        atualizado = False

        for index, item in enumerate(rascunhos):
            if str(item.get("id") or "") == rascunho["id"]:
                rascunho["criado_em"] = _texto(item.get("criado_em"), rascunho["criado_em"])
                rascunhos[index] = rascunho
                atualizado = True
                break

        if not atualizado:
            rascunhos.insert(0, rascunho)

        rascunhos.sort(key=lambda item: str(item.get("atualizado_em") or ""), reverse=True)
        _salvar_banco(rascunhos[:max_entries])

    return rascunho


def excluir_rascunho_cliente(rascunho_id: str) -> bool:
    draft_id = _texto(rascunho_id)

    if not draft_id:
        return False

    path = _db_path()

    with _file_lock(path):
        rascunhos = _ler_banco()
        filtrados = [item for item in rascunhos if str(item.get("id") or "") != draft_id]

        if len(filtrados) == len(rascunhos):
            return False

        _salvar_banco(filtrados)
        return True


def diagnostico_rascunhos() -> dict[str, Any]:
    root = _drafts_root()
    path = _db_path()

    return {
        "enabled": bool(get_setting("drafts", "enabled", default=True)),
        "root": str(root),
        "db_file": str(path),
        "exists": path.exists(),
        "count": len(_ler_banco()),
    }
