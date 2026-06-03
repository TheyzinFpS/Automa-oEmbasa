from __future__ import annotations

import getpass
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.documentos import formatar_doc, limpar_doc
from backend.flows.multa_contratual import (
    TIPO_MULTA_CONTRATUAL,
    montar_texto_multa_contratual,
)
from backend.settings import get_project_root, get_runtime_root, get_setting


TIPOS_DESCRICAO = {
    "viabilidade": "ANÁLISE DE VIABILIDADE TÉCNICA",
    "agua": "APROVAÇÃO DE PROJETO DE ABASTECIMENTO DE ÁGUA",
    "esgoto": "APROVAÇÃO DE PROJETO DE ESGOTAMENTO SANITÁRIO",
    "agua_esgoto": (
        "APROVAÇÃO DE PROJETOS DE ABASTECIMENTO DE ÁGUA "
        "E ESGOTAMENTO SANITÁRIO"
    ),
    TIPO_MULTA_CONTRATUAL: "MULTA CONTRATUAL",
}

TIPOS_LABEL = {
    "viabilidade": "Viabilidade",
    "agua": "Projeto Água",
    "esgoto": "Projeto Esgoto",
    TIPO_MULTA_CONTRATUAL: "Multa Contratual",
    "agua_esgoto": "Projeto Água + Esgoto",
}


def _agora() -> datetime:
    return datetime.now()


def _texto(valor: Any, fallback: str = "") -> str:
    texto = str(valor or "").strip()
    return texto or fallback


def _slug(valor: Any, fallback: str = "registro") -> str:
    texto = _texto(valor, fallback).upper()
    texto = re.sub(r"[^\w\s.-]", "", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", "_", texto)
    texto = texto.strip("._-")
    return texto[:90] or fallback


def _resolver_caminho_configurado(valor: str, fallback: Path) -> Path:
    caminho = Path(str(valor or "").strip()) if valor else fallback

    if not caminho.is_absolute():
        caminho = get_project_root() / caminho

    return caminho


def _history_root() -> Path:
    configurado = get_setting("history", "shared_dir", default="")
    fallback = get_runtime_root() / "historico"
    root = _resolver_caminho_configurado(configurado, fallback)

    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except Exception:
        if get_setting("history", "fallback_to_local", default=True):
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        raise


def _db_path() -> Path:
    file_name = get_setting("history", "db_file", default="historico_pedidos.json")
    return _history_root() / str(file_name or "historico_pedidos.json")


@contextmanager
def _file_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    timeout = float(get_setting("history", "lock_timeout_seconds", default=5) or 5)
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


def _ler_banco() -> list[dict[str, Any]]:
    path = _db_path()

    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []

    if isinstance(payload, dict):
        registros = payload.get("registros")
        return registros if isinstance(registros, list) else []

    return payload if isinstance(payload, list) else []


def _salvar_banco(registros: list[dict[str, Any]]) -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "schema": 1,
        "atualizado_em": _agora().isoformat(timespec="seconds"),
        "registros": registros,
    }
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _tipo_documento_info(documento: str) -> dict[str, str]:
    digitos = limpar_doc(documento)

    if len(digitos) == 14:
        return {
            "tipo": "cnpj",
            "rotulo": "CNPJ",
            "pessoa": "juridica",
            "pessoa_label": "Pessoa Jurídica",
        }

    if len(digitos) == 11:
        return {
            "tipo": "cpf",
            "rotulo": "CPF",
            "pessoa": "fisica",
            "pessoa_label": "Pessoa Física",
        }

    return {
        "tipo": "",
        "rotulo": "CPF/CNPJ",
        "pessoa": "",
        "pessoa_label": "Não identificado",
    }


def _normalizar_endereco(endereco: dict[str, Any] | None) -> dict[str, str]:
    endereco = dict(endereco or {})
    cep = _texto(endereco.get("cep"), "SEM CEP").upper()
    numero = _texto(endereco.get("numero"), "S/N").upper()

    if bool(endereco.get("sem_numero")) or numero in {"S/N", "SN", "SEM NUMERO", "SEM NÚMERO"}:
        numero = "S/N"

    if bool(endereco.get("sem_cep")) or cep in {"SEM CEP", "SEM-CEP", "S/CEP"}:
        cep = "SEM CEP"

    return {
        "empreendimento": _texto(endereco.get("empreendimento")).upper(),
        "rua": _texto(endereco.get("rua")).upper(),
        "numero": numero,
        "bairro": _texto(endereco.get("bairro")).upper(),
        "complemento": _texto(endereco.get("complemento")).upper(),
        "cidade": _texto(endereco.get("cidade")).upper(),
        "estado": _texto(endereco.get("estado"), "BA").upper(),
        "cep": cep,
    }


def montar_texto_padrao(dados: dict[str, Any], resultado: dict[str, Any] | None = None) -> str:
    tipo = _texto(dados.get("tipo") or (resultado or {}).get("tipo")).lower()

    if tipo == TIPO_MULTA_CONTRATUAL:
        dados_multa = {
            **(dados or {}),
            "nome_cliente": (
                (resultado or {}).get("nome_cliente")
                or dados.get("nome_cliente")
                or dados.get("razao_social")
            ),
        }
        return montar_texto_multa_contratual(dados_multa)

    endereco = _normalizar_endereco(dados.get("endereco"))
    descricao = TIPOS_DESCRICAO.get(tipo, _texto(tipo, "SOLICITAÇÃO SAP").upper())
    logradouro = f"{endereco['rua']}, {endereco['numero']}".strip(", ")

    if endereco["complemento"]:
        logradouro = f"{logradouro}, {endereco['complemento']}"

    return (
        f"Referente à solicitação de {descricao}, "
        f"no empreendimento {endereco['empreendimento']}, localizado na "
        f"{logradouro}, bairro {endereco['bairro']}, "
        f"{endereco['cidade']}-{endereco['estado']}, CEP: {endereco['cep']}."
    )


def _texto_bol(valor: Any) -> str:
    texto = _texto(valor)

    if not texto:
        return ""

    if texto.upper() in {"GERADO", "LINHA_SELECIONADA", "--"}:
        return ""

    return texto


def _numero_bol(resultado: dict[str, Any]) -> str:
    direto = (
        _texto_bol(resultado.get("numero_bol"))
        or _texto_bol(resultado.get("identificacao_pagamento"))
    )

    if direto:
        return direto

    identificacoes = resultado.get("identificacoes_pagamento")

    if isinstance(identificacoes, dict):
        partes = []

        for tipo, valor in identificacoes.items():
            bol = _texto_bol(valor)

            if bol:
                label = TIPOS_LABEL.get(str(tipo or "").lower(), _texto(tipo, "Tipo"))
                partes.append(f"{label}: {bol}")

        if partes:
            return " | ".join(partes)

    agua_esgoto = resultado.get("agua_esgoto")

    if isinstance(agua_esgoto, list):
        partes = []

        for item in agua_esgoto:
            if not isinstance(item, dict):
                continue

            bol = _texto_bol(item.get("identificacao_pagamento"))

            if bol:
                label = _texto(
                    item.get("tipo_label")
                    or TIPOS_LABEL.get(str(item.get("tipo") or "").lower()),
                    "Tipo",
                )
                partes.append(f"{label}: {bol}")

        if partes:
            return " | ".join(partes)

    return _texto_bol(resultado.get("boleto"))


def _montar_registro(dados: dict[str, Any], resultado: dict[str, Any]) -> dict[str, Any]:
    agora = _agora()
    documento = limpar_doc(dados.get("doc") or resultado.get("documento") or "")
    doc_info = _tipo_documento_info(documento)
    endereco = _normalizar_endereco(dados.get("endereco"))
    nome_cliente = _texto(
        resultado.get("nome_cliente")
        or dados.get("nome_cliente")
        or resultado.get("cliente_nome")
        or resultado.get("razao_social"),
        "Cliente não identificado",
    )
    numero_pedido = _texto(
        resultado.get("pedido")
        or resultado.get("numero_pedido")
        or resultado.get("ordem")
        or resultado.get("faturamento")
        or resultado.get("doc_fat"),
        "Não informado",
    )
    tipo = _texto(dados.get("tipo") or resultado.get("tipo")).lower()
    usuario = _texto(getpass.getuser(), "usuario")
    texto_padrao = montar_texto_padrao(dados, resultado)
    numero_bol = _numero_bol(resultado)
    registro_id = f"{agora.strftime('%Y%m%d%H%M%S')}_{_slug(numero_pedido, 'pedido')}"

    return {
        "id": registro_id,
        "data": agora.strftime("%Y-%m-%d"),
        "hora": agora.strftime("%H:%M:%S"),
        "data_hora": agora.isoformat(timespec="seconds"),
        "usuario": usuario,
        "nome_cliente": nome_cliente,
        "documento": documento,
        "documento_formatado": formatar_doc(documento),
        "tipo_documento": doc_info["rotulo"],
        "tipo_pessoa": doc_info["pessoa"],
        "tipo_pessoa_label": doc_info["pessoa_label"],
        "numero_cliente": _texto(resultado.get("cliente"), "Não informado"),
        "numero_pedido": numero_pedido,
        "faturamento": _texto(resultado.get("faturamento")),
        "doc_fat": _texto(resultado.get("doc_fat")),
        "numero_bol": numero_bol,
        "boleto": _texto(resultado.get("boleto")),
        "identificacao_pagamento": _texto(resultado.get("identificacao_pagamento")),
        "tipo_solicitacao": tipo,
        "tipo_solicitacao_label": TIPOS_LABEL.get(tipo, _texto(tipo, "Não informado")),
        "valor": _texto(resultado.get("valor") or dados.get("valor")),
        "contrato": _texto(resultado.get("contrato") or dados.get("contrato")),
        "endereco": endereco,
        "texto_padrao": texto_padrao,
        "origem": "EmbasaPedidosSAP",
    }


def _conteudo_txt(registro: dict[str, Any]) -> str:
    endereco = registro.get("endereco") or {}
    linhas = [
        "HISTÓRICO DE PEDIDO SAP - EMBASA",
        "=" * 42,
        f"Data/Hora: {registro.get('data_hora', '')}",
        f"Usuário Windows: {registro.get('usuario', '')}",
        "",
        "CLIENTE",
        f"Nome: {registro.get('nome_cliente', '')}",
        f"Documento: {registro.get('documento_formatado', '')} ({registro.get('tipo_pessoa_label', '')})",
        f"Número do cliente SAP: {registro.get('numero_cliente', '')}",
        "",
        "PEDIDO",
        f"Número do pedido: {registro.get('numero_pedido', '')}",
        f"Doc. fat: {registro.get('doc_fat') or registro.get('faturamento') or ''}",
        f"Numero do BOL: {registro.get('numero_bol') or registro.get('identificacao_pagamento') or registro.get('boleto') or ''}",
        f"Tipo de solicitação: {registro.get('tipo_solicitacao_label', '')}",
        f"Valor: {registro.get('valor', '')}",
        "",
        "ENDEREÇO DO EMPREENDIMENTO",
        f"Empreendimento: {endereco.get('empreendimento', '')}",
        f"Rua: {endereco.get('rua', '')}",
        f"Número: {endereco.get('numero', '')}",
        f"Bairro: {endereco.get('bairro', '')}",
        f"Complemento: {endereco.get('complemento', '')}",
        f"Cidade/Estado: {endereco.get('cidade', '')}-{endereco.get('estado', '')}",
        f"CEP: {endereco.get('cep', '')}",
        "",
        "TEXTO PADRÃO VA01",
        registro.get("texto_padrao", ""),
        "",
    ]
    contrato = _texto(registro.get("contrato"))

    if contrato:
        indice_endereco = next(
            (
                indice
                for indice, linha in enumerate(linhas)
                if str(linha).startswith("ENDERE")
            ),
            len(linhas),
        )
        linhas.insert(max(0, indice_endereco - 1), f"Contrato: {contrato}")

    return "\n".join(linhas)


def _salvar_txt(registro: dict[str, Any]) -> Path:
    root = _history_root()
    data = _slug(registro.get("data"), "sem_data")
    usuario = _slug(registro.get("usuario"), "usuario")
    cliente = _slug(registro.get("nome_cliente"), "cliente")
    pedido = _slug(registro.get("numero_pedido"), "pedido")
    pasta = root / "txt" / data / usuario / cliente
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{registro.get('data', '')}_{pedido}_{registro.get('id', '')}.txt"
    caminho.write_text(_conteudo_txt(registro), encoding="utf-8")
    return caminho


def registrar_historico_pedido(
    dados: dict[str, Any],
    resultado: dict[str, Any],
    logger=None,
) -> dict[str, Any] | None:
    if not get_setting("history", "enabled", default=True):
        return None

    registro = _montar_registro(dados, resultado or {})

    try:
        txt_path = _salvar_txt(registro)
        registro["txt_path"] = str(txt_path)

        db_path = _db_path()
        with _file_lock(db_path):
            registros = _ler_banco()
            registros.append(registro)
            max_entries = int(get_setting("history", "max_entries", default=5000) or 5000)
            registros = registros[-max_entries:]
            _salvar_banco(registros)

        if logger:
            logger.add(
                -1,
                f"Histórico registrado para o pedido {registro['numero_pedido']}.",
                publico=False,
            )
        return registro
    except Exception as exc:
        if logger:
            logger.add(
                -1,
                f"Não foi possível registrar histórico do pedido: {exc}",
                nivel="DEBUG",
                publico=False,
            )
        return None


def _registro_resumo(registro: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": registro.get("id"),
        "data": registro.get("data"),
        "hora": registro.get("hora"),
        "nome_cliente": registro.get("nome_cliente"),
        "documento_formatado": registro.get("documento_formatado"),
        "tipo_pessoa_label": registro.get("tipo_pessoa_label"),
        "numero_cliente": registro.get("numero_cliente"),
        "numero_pedido": registro.get("numero_pedido"),
        "doc_fat": registro.get("doc_fat"),
        "numero_bol": registro.get("numero_bol"),
        "contrato": registro.get("contrato"),
        "tipo_solicitacao_label": registro.get("tipo_solicitacao_label"),
        "empreendimento": (registro.get("endereco") or {}).get("empreendimento"),
    }


def listar_historico_pedidos(filtro: str = "", limite: int | None = None) -> list[dict[str, Any]]:
    filtro_norm = _texto(filtro).upper()
    limite = limite or int(get_setting("history", "max_results", default=200) or 200)
    registros = sorted(_ler_banco(), key=lambda item: item.get("data_hora", ""), reverse=True)

    if filtro_norm:
        registros = [
            registro
            for registro in registros
            if filtro_norm
            in " ".join(
                _texto(registro.get(campo)).upper()
                for campo in (
                    "data",
                    "hora",
                    "nome_cliente",
                    "documento",
                    "documento_formatado",
                    "numero_cliente",
                    "numero_pedido",
                    "doc_fat",
                    "numero_bol",
                    "boleto",
                    "identificacao_pagamento",
                    "tipo_solicitacao_label",
                )
            )
            or filtro_norm in _texto((registro.get("endereco") or {}).get("empreendimento")).upper()
        ]

    return [_registro_resumo(registro) for registro in registros[:limite]]


def obter_historico_pedido(registro_id: str) -> dict[str, Any] | None:
    registro_id = _texto(registro_id)

    if not registro_id:
        return None

    for registro in _ler_banco():
        if _texto(registro.get("id")) == registro_id:
            return registro

    return None


def diagnostico_historico() -> dict[str, Any]:
    root = _history_root()
    db = _db_path()
    return {
        "enabled": bool(get_setting("history", "enabled", default=True)),
        "root": str(root),
        "db_file": str(db),
        "total": len(_ler_banco()),
    }
