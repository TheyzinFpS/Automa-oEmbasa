from __future__ import annotations

import re
from typing import Any

from backend.documentos import formatar_doc, limpar_doc


TIPO_MULTA_CONTRATUAL = "multa_contratual"
LABEL_MULTA_CONTRATUAL = "Multa Contratual"
PDF_LABEL_MULTA_CONTRATUAL = "MULTA CONTRATUAL"

_UNIDADES = (
    "zero",
    "um",
    "dois",
    "três",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
)
_DEZ_A_DEZENOVE = (
    "dez",
    "onze",
    "doze",
    "treze",
    "quatorze",
    "quinze",
    "dezesseis",
    "dezessete",
    "dezoito",
    "dezenove",
)
_DEZENAS = (
    "",
    "",
    "vinte",
    "trinta",
    "quarenta",
    "cinquenta",
    "sessenta",
    "setenta",
    "oitenta",
    "noventa",
)
_CENTENAS = (
    "",
    "cento",
    "duzentos",
    "trezentos",
    "quatrocentos",
    "quinhentos",
    "seiscentos",
    "setecentos",
    "oitocentos",
    "novecentos",
)


def _texto(valor: Any, fallback: str = "") -> str:
    texto = str(valor or "").strip()
    return texto or fallback


def _limpar_parte_nome_arquivo(valor: Any, fallback: str = "INFORMAR") -> str:
    texto = _texto(valor, fallback)
    texto = re.sub(r'[<>:"/\\|?*]+', "-", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" .-") or fallback


def normalizar_contrato(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())[:9]


def _centavos_from_dados(dados: dict[str, Any]) -> int:
    valor_info = dados.get("valor_info") or {}

    try:
        return int(valor_info.get("centavos"))
    except Exception:
        pass

    valor = str(dados.get("valor") or "")
    digitos = "".join(ch for ch in valor if ch.isdigit())
    return int(digitos or "0")


def _formatar_centavos(centavos: int) -> str:
    reais, cents = divmod(max(0, int(centavos or 0)), 100)
    inteiro = f"{reais:,}".replace(",", ".")
    return f"R$ {inteiro},{cents:02d}"


def formatar_valor_pdf(dados: dict[str, Any]) -> str:
    valor_info = dados.get("valor_info") or {}
    formatado = _texto(valor_info.get("formatado") or dados.get("valor"))

    if not formatado:
        formatado = _formatar_centavos(_centavos_from_dados(dados))

    if formatado.startswith("R$ "):
        return "R$" + formatado[3:]

    return formatado


def _numero_ate_999(numero: int) -> str:
    numero = int(numero or 0)

    if numero < 10:
        return _UNIDADES[numero]

    if numero < 20:
        return _DEZ_A_DEZENOVE[numero - 10]

    if numero < 100:
        dezena, unidade = divmod(numero, 10)
        texto = _DEZENAS[dezena]
        return f"{texto} e {_UNIDADES[unidade]}" if unidade else texto

    if numero == 100:
        return "cem"

    centena, resto = divmod(numero, 100)
    texto = _CENTENAS[centena]
    return f"{texto} e {_numero_ate_999(resto)}" if resto else texto


def _juntar_partes_extenso(partes: list[str]) -> str:
    partes = [parte for parte in partes if parte]

    if not partes:
        return "zero"

    if len(partes) == 1:
        return partes[0]

    return " e ".join([", ".join(partes[:-1]), partes[-1]])


def numero_por_extenso(numero: int) -> str:
    numero = int(numero or 0)

    if numero == 0:
        return "zero"

    grupos = []
    bilhoes, resto = divmod(numero, 1_000_000_000)
    milhoes, resto = divmod(resto, 1_000_000)
    milhares, unidades = divmod(resto, 1_000)

    if bilhoes:
        grupos.append(
            "um bilhão" if bilhoes == 1 else f"{_numero_ate_999(bilhoes)} bilhões"
        )

    if milhoes:
        grupos.append(
            "um milhão" if milhoes == 1 else f"{_numero_ate_999(milhoes)} milhões"
        )

    if milhares:
        grupos.append("mil" if milhares == 1 else f"{_numero_ate_999(milhares)} mil")

    if unidades:
        grupos.append(_numero_ate_999(unidades))

    return _juntar_partes_extenso(grupos)


def valor_por_extenso(centavos: int) -> str:
    reais, cents = divmod(max(0, int(centavos or 0)), 100)
    partes = []

    if reais:
        partes.append(
            f"{numero_por_extenso(reais)} {'real' if reais == 1 else 'reais'}"
        )

    if cents:
        partes.append(
            f"{numero_por_extenso(cents)} {'centavo' if cents == 1 else 'centavos'}"
        )

    return " e ".join(partes) if partes else "zero real"


def montar_texto_multa_contratual(
    dados: dict[str, Any],
    nome_cliente: str | None = None,
) -> str:
    nome = _texto(
        nome_cliente
        or dados.get("nome_cliente")
        or dados.get("cliente_nome")
        or dados.get("razao_social")
        or dados.get("nome1"),
        "CLIENTE NAO IDENTIFICADO",
    ).upper()
    doc = _texto((dados.get("doc_info") or {}).get("formatado") or formatar_doc(dados.get("doc", "")))
    doc_limpo = limpar_doc(doc or dados.get("doc", ""))
    rotulo_doc = "CNPJ" if len(doc_limpo) == 14 else "CPF"
    valor_pdf = formatar_valor_pdf(dados)
    extenso = valor_por_extenso(_centavos_from_dados(dados))

    return (
        f"Valor da multa contratual: {valor_pdf} ({extenso}).\n"
        f"Empresa: {nome}.\n"
        f"{rotulo_doc} n° {doc}."
    )


def montar_nome_pdf_multa_contratual(
    numero_boleto: Any,
    dados: dict[str, Any] | None = None,
    cliente: Any = None,
) -> str:
    dados = dados or {}
    contrato = normalizar_contrato(dados.get("contrato")) or "CONTRATO"
    valor_pdf = formatar_valor_pdf(dados)
    documento = (dados.get("doc_info") or {}).get("formatado") or formatar_doc(
        dados.get("doc", "")
    )
    nome_cliente = _texto(
        dados.get("nome_cliente")
        or dados.get("cliente_nome")
        or dados.get("razao_social")
        or dados.get("nome")
        or dados.get("nome1"),
        f"CLIENTE {cliente}" if cliente else f"NOME DO CLIENTE OU EMPRESA {documento}",
    )

    partes = [
        _limpar_parte_nome_arquivo(numero_boleto, "DOC_FAT"),
        _limpar_parte_nome_arquivo(nome_cliente, "NOME DO CLIENTE OU EMPRESA"),
        PDF_LABEL_MULTA_CONTRATUAL,
        _limpar_parte_nome_arquivo(contrato, "CONTRATO"),
        _limpar_parte_nome_arquivo(valor_pdf, "VALOR"),
    ]

    return " - ".join(partes) + ".pdf"
