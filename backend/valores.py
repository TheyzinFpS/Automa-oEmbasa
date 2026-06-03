import re


MAX_VALOR_CENTAVOS = 1_000_000


# Remove simbolos e separadores, mantendo apenas centavos em digitos.
def limpar_valor(valor):
    return re.sub(r"\D", "", str(valor or ""))


# Converte a entrada monetaria para centavos e aplica limite maximo.
def valor_para_centavos(valor, limite_centavos=MAX_VALOR_CENTAVOS):
    digitos = limpar_valor(valor)

    if not digitos:
        raise ValueError("Valor não informado")

    centavos = int(digitos)

    if centavos <= 0:
        raise ValueError("Valor deve ser maior que zero")

    if limite_centavos is not None and centavos > limite_centavos:
        raise ValueError(
            f"Valor não pode ultrapassar {formatar_centavos(limite_centavos)}"
        )

    return centavos


# Formata centavos no padrao brasileiro usado pela UI e pelo SAP.
def formatar_centavos(centavos, com_simbolo=True):
    inteiro = centavos // 100
    casas = centavos % 100
    valor = f"{inteiro:,}".replace(",", ".") + f",{casas:02d}"

    if com_simbolo:
        return f"R$ {valor}"

    return valor


# Gera todas as representacoes do valor usadas no fluxo.
def analisar_valor(valor):
    centavos = valor_para_centavos(valor)

    return {
        "centavos": centavos,
        "formatado": formatar_centavos(centavos, com_simbolo=True),
        "sap": formatar_centavos(centavos, com_simbolo=False),
        "limite": formatar_centavos(MAX_VALOR_CENTAVOS, com_simbolo=True),
    }


def analisar_valor_sem_limite(valor):
    centavos = valor_para_centavos(valor, limite_centavos=None)

    return {
        "centavos": centavos,
        "formatado": formatar_centavos(centavos, com_simbolo=True),
        "sap": formatar_centavos(centavos, com_simbolo=False),
        "limite": None,
    }
