import re


MAX_VALOR_CENTAVOS = 1_000_000


def limpar_valor(valor):
    return re.sub(r"\D", "", str(valor or ""))


def valor_para_centavos(valor):
    digitos = limpar_valor(valor)

    if not digitos:
        raise ValueError("Valor não informado")

    centavos = int(digitos)

    if centavos <= 0:
        raise ValueError("Valor deve ser maior que zero")

    if centavos > MAX_VALOR_CENTAVOS:
        raise ValueError("Valor não pode ultrapassar R$ 10.000,00")

    return centavos


def formatar_centavos(centavos, com_simbolo=True):
    inteiro = centavos // 100
    casas = centavos % 100
    valor = f"{inteiro:,}".replace(",", ".") + f",{casas:02d}"

    if com_simbolo:
        return f"R$ {valor}"

    return valor


def analisar_valor(valor):
    centavos = valor_para_centavos(valor)

    return {
        "centavos": centavos,
        "formatado": formatar_centavos(centavos, com_simbolo=True),
        "sap": formatar_centavos(centavos, com_simbolo=False),
        "limite": formatar_centavos(MAX_VALOR_CENTAVOS, com_simbolo=True),
    }
