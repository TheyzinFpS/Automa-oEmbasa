import re


def limpar_doc(valor):
    return re.sub(r"\D", "", str(valor or ""))


def tipo_documento(doc):
    doc_limpo = limpar_doc(doc)

    if len(doc_limpo) == 11:
        return "cpf"

    if len(doc_limpo) == 14:
        return "cnpj"

    raise ValueError(
        f"Documento invalido: esperado 11 (CPF) ou 14 (CNPJ), recebido {len(doc_limpo)}"
    )


def formatar_doc(doc):
    digitos = limpar_doc(doc)[:14]

    if len(digitos) <= 11:
        partes = []

        if digitos[:3]:
            partes.append(digitos[:3])

        if digitos[3:6]:
            partes.append(digitos[3:6])

        cpf_base = ".".join(partes)

        if digitos[6:9]:
            cpf_base = f"{cpf_base}.{digitos[6:9]}" if cpf_base else digitos[6:9]

        if digitos[9:11]:
            return f"{cpf_base}-{digitos[9:11]}" if cpf_base else digitos[9:11]

        return cpf_base or digitos

    cnpj_base = digitos[:2]

    if digitos[2:5]:
        cnpj_base += f".{digitos[2:5]}"

    if digitos[5:8]:
        cnpj_base += f".{digitos[5:8]}"

    if digitos[8:12]:
        cnpj_base += f"/{digitos[8:12]}"

    if digitos[12:14]:
        cnpj_base += f"-{digitos[12:14]}"

    return cnpj_base


def analisar_doc(doc):
    digitos = limpar_doc(doc)[:14]
    total = len(digitos)

    if total == 0:
        return {
            "digitos": "",
            "formatado": "",
            "tipo": None,
            "rotulo": "CPF/CNPJ",
            "valido": False,
            "faltam": 11,
        }

    if total <= 11:
        faltam = max(0, 11 - total)
        return {
            "digitos": digitos,
            "formatado": formatar_doc(digitos),
            "tipo": "cpf" if total == 11 else None,
            "rotulo": "CPF",
            "valido": total == 11,
            "faltam": faltam,
        }

    faltam = max(0, 14 - total)
    return {
        "digitos": digitos,
        "formatado": formatar_doc(digitos),
        "tipo": "cnpj" if total == 14 else None,
        "rotulo": "CNPJ",
        "valido": total == 14,
        "faltam": faltam,
    }
