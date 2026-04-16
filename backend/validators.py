from backend.documentos import limpar_doc, tipo_documento
from backend.valores import analisar_valor


def _texto_preenchido(valor):
    return bool(str(valor or "").strip())


def _texto_tem_digitos(valor):
    return any(char.isdigit() for char in str(valor or ""))


def validar_dados(dados):
    erros = []

    doc = limpar_doc(dados.get("doc", ""))

    try:
        tipo_documento(doc)
    except ValueError:
        erros.append("CPF/CNPJ inválido")

    if not dados.get("tipo"):
        erros.append("Tipo não selecionado")

    try:
        analisar_valor(dados.get("valor", ""))
    except ValueError as exc:
        erros.append(str(exc))

    endereco = dados.get("endereco") or {}
    cep = "".join(filter(str.isdigit, str(endereco.get("cep", ""))))

    if not _texto_preenchido(endereco.get("empreendimento")):
        erros.append("Empreendimento obrigatorio")

    if not _texto_preenchido(endereco.get("rua")):
        erros.append("Rua do empreendimento obrigatoria")

    if not _texto_preenchido(endereco.get("numero")):
        erros.append("Numero do empreendimento obrigatorio")

    if len(cep) != 8:
        erros.append("CEP do empreendimento obrigatório")

    if not _texto_preenchido(endereco.get("bairro")):
        erros.append("Bairro do empreendimento obrigatorio")

    if not _texto_preenchido(endereco.get("cidade")):
        erros.append("Cidade do empreendimento obrigatoria")
    elif _texto_tem_digitos(endereco.get("cidade")):
        erros.append("Cidade do empreendimento deve conter apenas letras")

    return erros
