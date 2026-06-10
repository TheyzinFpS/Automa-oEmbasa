from backend.documentos import limpar_doc, tipo_documento
from backend.valores import analisar_valor, analisar_valor_sem_limite


# Verifica se o campo textual tem algum conteúdo útil.
def _texto_preenchido(valor):
    return bool(str(valor or "").strip())


# Ajuda a impedir números em campos que devem aceitar somente texto.
def _texto_tem_digitos(valor):
    return any(char.isdigit() for char in str(valor or ""))


# Identifica endereços rurais ou sem CEP cadastrado na consulta pública.
def _endereco_sem_cep(endereco):
    cep_original = str(endereco.get("cep", "")).strip().upper()
    return bool(endereco.get("sem_cep")) or cep_original in {
        "SEM CEP",
        "SEM-CEP",
        "S/CEP",
    }


# Valida os dados obrigatórios antes de iniciar a automação SAP.
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
    sem_cep = _endereco_sem_cep(endereco)

    if not _texto_preenchido(endereco.get("empreendimento")):
        erros.append("Empreendimento obrigatório")

    if not _texto_preenchido(endereco.get("rua")):
        erros.append("Rua do empreendimento obrigatória")

    if not _texto_preenchido(endereco.get("numero")):
        erros.append("Número do empreendimento obrigatório")

    if not sem_cep and len(cep) != 8:
        erros.append("CEP do empreendimento obrigatório")

    if not _texto_preenchido(endereco.get("bairro")):
        erros.append("Bairro do empreendimento obrigatório")

    if not _texto_preenchido(endereco.get("cidade")):
        erros.append("Cidade do empreendimento obrigatória")
    elif _texto_tem_digitos(endereco.get("cidade")):
        erros.append("Cidade do empreendimento deve conter apenas letras")

    return erros


def validar_dados_multa_contratual(dados):
    erros = []
    doc = limpar_doc(dados.get("doc", ""))

    try:
        tipo_documento(doc)
    except ValueError:
        erros.append("CPF/CNPJ inválido")

    try:
        analisar_valor_sem_limite(dados.get("valor", ""))
    except ValueError as exc:
        erros.append(str(exc))

    contrato = "".join(filter(str.isdigit, str(dados.get("contrato", ""))))

    if not contrato:
        erros.append("Número do contrato obrigatório")
    elif len(contrato) > 9:
        erros.append("Número do contrato deve ter no máximo 9 dígitos")

    validade = "".join(filter(str.isdigit, str(dados.get("validade_dias_uteis", ""))))

    if validade not in {"30", "60"}:
        erros.append("Data de validade da multa contratual obrigatoria")

    return erros
