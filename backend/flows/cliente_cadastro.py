import re
import unicodedata

from backend.documentos import limpar_doc, tipo_documento
from backend.flows.common import ler_status_texto, notificar_progresso, resultado_padrao
from backend.utils.sap_waits import (
    element_exists,
    press_and_wait,
    send_vkey_and_wait,
    wait_for_element,
    wait_until_ready,
)


VKORG_PADRAO = "EMBA"
VTWEG_PADRAO = "PO"
BUKRS_PADRAO = "EMBA"
SETOR_INICIAL_CADASTRO = "AE"
NOME_PARTE_LIMITE = 17
TEMA_PESQUISA_LIMITE = 17

TIPO_PARA_SETOR = {
    "viabilidade": ("AE",),
    "agua": ("AG",),
    "esgoto": ("EG",),
    "agua_esgoto": ("AG", "EG"),
}

SETOR_CONFIG = {
    "AE": {
        "vendas": "1055",
        "grupo": "DM",
        "descricao": "Viabilidade",
    },
    "AG": {
        "vendas": "1055",
        "grupo": "DM",
        "descricao": "Agua",
    },
    "EG": {
        "vendas": "1070",
        "grupo": "ME",
        "descricao": "Esgoto",
    },
}

ORDEM_SETORES = ("AE", "AG", "EG")
SETOR_JA_EXISTENTE_INDICADORES = (
    "ja existe",
    "already exists",
    "area de vendas ja",
    "area vendas ja",
    "ja criado",
    "ja cadastr",
)


def setores_necessarios_para_tipo(tipo):
    tipo_normalizado = str(tipo or "").strip().lower()
    return TIPO_PARA_SETOR.get(tipo_normalizado, ())


def _ordenar_setores(setores):
    solicitados = {
        str(setor or "").strip().upper()
        for setor in (setores or ())
        if str(setor or "").strip()
    }
    ordenados = [setor for setor in ORDEM_SETORES if setor in solicitados]
    ordenados.extend(sorted(setor for setor in solicitados if setor not in ORDEM_SETORES))

    return tuple(ordenados)


def _normalizar_texto_busca(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return texto.lower()


def _texto_indica_setor_existente(texto):
    normalizado = _normalizar_texto_busca(texto)
    return any(indicador in normalizado for indicador in SETOR_JA_EXISTENTE_INDICADORES)


def _textos_contexto_sap(session):
    textos = [ler_status_texto(session)]

    for element_id in (
        "wnd[1]/usr/txtMESSTXT1",
        "wnd[1]/usr/txtMESSTXT2",
        "wnd[1]/usr/txtSPOP-TEXTLINE1",
        "wnd[1]/usr/txtSPOP-TEXTLINE2",
        "wnd[1]/usr/txtSPOP-TEXTLINE3",
    ):
        try:
            textos.append(session.findById(element_id).text)
        except Exception:
            continue

    return " ".join(str(texto or "") for texto in textos)


def _erro_indica_setor_existente(session, exc=None):
    contexto = _textos_contexto_sap(session)

    if exc:
        contexto = f"{contexto} {exc}"

    return _texto_indica_setor_existente(contexto)


def _limitar_texto(valor, limite):
    texto = _normalizar_espacos(valor)
    return texto[: int(limite or 0)] if limite else texto


def _normalizar_espacos(valor):
    return re.sub(r"\s+", " ", str(valor or "")).strip()


def _dividir_nome(nome, nome2="", limite=NOME_PARTE_LIMITE):
    nome1 = _normalizar_espacos(nome)
    complemento = _normalizar_espacos(nome2)

    if complemento:
        return _limitar_texto(nome1, limite), _limitar_texto(complemento, limite)

    if len(nome1) <= limite:
        return nome1, ""

    corte = nome1.rfind(" ", 0, limite + 1)
    if corte < 12:
        corte = limite

    return nome1[:corte].strip(), nome1[corte:].strip()[:limite]


def _separar_tratamento_nome(nome):
    texto = _normalizar_espacos(nome)
    normalizado = texto.upper()

    regras = (
        ("SRA.", "Sra"),
        ("SRA ", "Sra"),
        ("SENHORA ", "Sra"),
        ("DONA ", "Sra"),
        ("DNA ", "Sra"),
        ("SR.", "Sr"),
        ("SR ", "Sr"),
        ("SENHOR ", "Sr"),
    )

    for prefixo, titulo in regras:
        if normalizado.startswith(prefixo):
            return titulo, texto[len(prefixo) :].strip()

    return "", texto


def _inferir_titulo_cliente(tipo_doc, nome, titulo_informado=""):
    titulo = str(titulo_informado or "").strip()

    if titulo and titulo.lower() != "auto":
        return titulo

    titulo_nome, _ = _separar_tratamento_nome(nome)

    if tipo_doc == "cnpj":
        return "Empresa"

    return titulo_nome or "Sr"


def _formatar_cep(valor):
    digitos = limpar_doc(valor)

    if len(digitos) != 8:
        raise ValueError("CEP obrigatorio deve conter 8 digitos.")

    return f"{digitos[:5]}-{digitos[5:]}"


def _normalizar_uf(valor):
    uf = re.sub(r"[^A-Za-z]", "", str(valor or "")).upper()[:2]

    if len(uf) != 2:
        raise ValueError("Estado obrigatorio deve ser informado pela sigla com 2 letras.")

    return uf


def _formatar_telefone(valor):
    digitos = limpar_doc(valor)

    if not digitos:
        return ""

    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"

    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"

    raise ValueError("Telefone deve ter 10 ou 11 digitos quando informado.")


def _grupo_tesouraria(tipo_doc):
    return "C-OUTRECPF" if tipo_doc == "cpf" else "C-OUTRECPJ"


def _normalizar_cadastro_cliente(dados):
    payload = dict(dados or {})
    doc = limpar_doc(payload.get("doc"))

    # Critério:
    # 11 dígitos = CPF / pessoa física
    # 14 dígitos = CNPJ / pessoa jurídica
    tipo_doc = tipo_documento(doc)
    tipo = str(payload.get("tipo") or "").strip().lower()
    setores = _ordenar_setores(
        payload.get("setores") or setores_necessarios_para_tipo(tipo)
    )

    if not setores:
        raise ValueError("Tipo de solicitacao sem setor SAP mapeado.")

    nome_base = (
        payload.get("nome1")
        or payload.get("razao_social")
        or payload.get("nome")
        or ""
    )
    titulo_detectado, nome_sem_tratamento = _separar_tratamento_nome(nome_base)
    nome1, nome2 = _dividir_nome(
        nome_sem_tratamento,
        payload.get("nome2"),
        NOME_PARTE_LIMITE,
    )
    sort1, sort2 = _dividir_nome(
        payload.get("sort1") or f"{nome_sem_tratamento} {payload.get('nome2') or ''}",
        payload.get("sort2"),
        TEMA_PESQUISA_LIMITE,
    )

    endereco = payload.get("endereco") or {}
    rua = payload.get("rua") or endereco.get("rua")
    numero = payload.get("numero") or endereco.get("numero")
    bairro = payload.get("bairro") or endereco.get("bairro")
    cep = payload.get("cep") or endereco.get("cep")
    cidade = payload.get("cidade") or endereco.get("cidade")
    estado = _normalizar_uf(payload.get("estado") or endereco.get("estado") or "BA")
    cep_formatado = _formatar_cep(cep)
    telefone_formatado = _formatar_telefone(payload.get("telefone") or "")

    obrigatorios = {
        "nome/razao social": nome1,
        "rua": rua,
        "numero": numero,
        "bairro": bairro,
        "cep": cep,
        "cidade": cidade,
        "estado": estado,
    }
    faltando = [rotulo for rotulo, valor in obrigatorios.items() if not str(valor or "").strip()]

    if faltando:
        raise ValueError("Campos obrigatorios ausentes: " + ", ".join(faltando))

    return {
        "doc": doc,
        "tipo_documento": tipo_doc,
        "tipo": tipo,
        "setores": setores,
        "grupo_conta": payload.get("grupo_conta")
        or ("PJ01" if tipo_doc == "cnpj" else "PF01"),
        "titulo": _inferir_titulo_cliente(
            tipo_doc,
            nome_base,
            payload.get("titulo") or titulo_detectado,
        ),
        "nome1": nome1,
        "nome2": nome2,
        "sort1": sort1,
        "sort2": sort2,
        "rua": _limitar_texto(rua, 60),
        "numero": _limitar_texto(numero, 10),
        "bairro": _limitar_texto(bairro, 40),
        "cep": cep_formatado,
        "cidade": _limitar_texto(cidade, 40).upper(),
        "estado": estado,
        "telefone": telefone_formatado,
        "email": _limitar_texto(payload.get("email") or "", 241),
        "inscricao_estadual": _limitar_texto(
            payload.get("inscricao_estadual") or "ISENTO",
            18,
        ),
    }


def _set_text(session, element_id, value, timeout=8, required=True):
    try:
        if not required:
            timeout = min(float(timeout or 1), 1.0)

        element = wait_for_element(session, element_id, timeout=timeout)
        texto = str(value or "")
        element.text = texto

        try:
            element.caretPosition = len(texto)
        except Exception:
            pass

        return element
    except Exception:
        if required:
            raise

    return None


def _set_key(session, element_id, value, timeout=8, required=True):
    try:
        if not required:
            timeout = min(float(timeout or 1), 1.0)

        element = wait_for_element(session, element_id, timeout=timeout)
        chave = str(value or "")

        try:
            element.key = chave
        except Exception:
            element.Key = chave

        return element
    except Exception:
        if required:
            raise

    return None



def _set_checkbox(session, element_id, selected=True, timeout=8, required=True):
    try:
        if not required:
            timeout = min(float(timeout or 1), 1.0)

        element = wait_for_element(session, element_id, timeout=timeout)

        try:
            element.selected = bool(selected)
        except Exception:
            element.Selected = bool(selected)

        return element

    except Exception:
        if required:
            raise

    return None


def _press(session, element_id, timeout=8, required=True):
    try:
        if not required:
            timeout = min(float(timeout or 1), 1.0)

        wait_for_element(session, element_id, timeout=timeout).press()
        wait_until_ready(session)
        return True
    except Exception:
        if required:
            raise

    return False


def _confirmar_popups_simples(session):
    for _ in range(3):
        confirmou = False

        for element_id in (
            "wnd[1]/tbar[0]/btn[0]",
            "wnd[1]/usr/btnSPOP-OPTION1",
            "wnd[1]/usr/btnBUTTON_1",
        ):
            try:
                session.findById(element_id).press()
                wait_until_ready(session)
                confirmou = True
                break
            except Exception:
                continue

        if not confirmou:
            return


def _abrir_xd01(session, logger):
    logger.add(0, "Abrindo XD01 para cadastro/area de vendas...")
    _set_text(session, "wnd[0]/tbar[0]/okcd", "/nXD01", timeout=10)
    send_vkey_and_wait(session, "wnd[0]", 0, "wnd[1]", timeout=10)


def _preencher_primeira_tela(
    session,
    grupo_conta,
    setor,
    cliente="",
    incluir_empresa=True,
):
    if grupo_conta:
        _set_key(session, "wnd[1]/usr/cmbRF02D-KTOKD", grupo_conta, required=False)

    _set_text(session, "wnd[1]/usr/ctxtRF02D-KUNNR", cliente, required=False)

    if incluir_empresa:
        _set_text(session, "wnd[1]/usr/ctxtRF02D-BUKRS", BUKRS_PADRAO, required=False)

    _set_text(session, "wnd[1]/usr/ctxtRF02D-VKORG", VKORG_PADRAO)
    _set_text(session, "wnd[1]/usr/ctxtRF02D-VTWEG", VTWEG_PADRAO)
    _set_text(session, "wnd[1]/usr/ctxtRF02D-SPART", setor)
    press_and_wait(session, "wnd[1]/tbar[0]/btn[0]")


def _preencher_dados_gerais(session, dados):
    if dados.get("titulo"):
        _set_key(
            session,
            "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
            "ssubSUBSC:SAPLATAB:0201/subAREA1:SAPMF02D:7111/"
            "subADDRESS:SAPLSZA1:0300/subCOUNTRY_SCREEN:SAPLSZA1:0301/"
            "cmbSZA1_D0100-TITLE_MEDI",
            dados["titulo"],
            required=True,
        )

    prefixo = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
        "ssubSUBSC:SAPLATAB:0201/subAREA1:SAPMF02D:7111/"
        "subADDRESS:SAPLSZA1:0300/subCOUNTRY_SCREEN:SAPLSZA1:0301/"
    )

    _set_text(session, prefixo + "txtADDR1_DATA-NAME1", dados["nome1"])
    _set_text(session, prefixo + "txtADDR1_DATA-NAME2", dados["nome2"], required=False)
    _set_text(session, prefixo + "txtADDR1_DATA-SORT1", dados["sort1"], required=False)
    _set_text(session, prefixo + "txtADDR1_DATA-SORT2", dados["sort2"], required=False)
    _set_text(session, prefixo + "txtADDR1_DATA-STREET", dados["rua"])
    _set_text(session, prefixo + "txtADDR1_DATA-HOUSE_NUM1", dados["numero"])
    _set_text(session, prefixo + "txtADDR1_DATA-CITY2", dados["bairro"])
    _set_text(session, prefixo + "txtADDR1_DATA-POST_CODE1", dados["cep"])
    _set_text(session, prefixo + "txtADDR1_DATA-CITY1", dados["cidade"])
    _set_text(session, prefixo + "ctxtADDR1_DATA-COUNTRY", "BR")
    _set_text(session, prefixo + "ctxtADDR1_DATA-REGION", dados["estado"])
    _set_text(session, prefixo + "txtSZA1_D0100-TEL_NUMBER", dados["telefone"], required=False)
    _set_text(session, prefixo + "txtSZA1_D0100-SMTP_ADDR", dados["email"], required=False)


def _preencher_documentos_fiscais(session, dados):
    tab = "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB02"
    wait_for_element(session, tab, timeout=8).select()
    wait_until_ready(session)

    prefixo = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB02/"
        "ssubSUBSC:SAPLATAB:0200/subAREA3:SAPMF02D:7122/"
    )

    if dados["tipo_documento"] == "cnpj":
        # Pessoa jurídica: preenche CNPJ e Inscrição Estadual como ISENTO.
        _set_text(session, prefixo + "txtKNA1-STCD1", dados["doc"])
        _set_text(
            session,
            prefixo + "txtKNA1-STCD3",
            dados["inscricao_estadual"],
        )

    else:
        # Pessoa física: preenche CPF e marca a checkbox "Pessoa física".
        # Não preenche inscrição estadual/ISENTO para pessoa física.
        _set_text(session, prefixo + "txtKNA1-STCD2", dados["doc"])

        # Campo SAP padrão de pessoa física: KNA1-STKZN.
        # O ID pode variar por layout, por isso tentamos variações sem travar.
        for checkbox_id in (
            prefixo + "chkKNA1-STKZN",
            prefixo + "chkKNA1-STKZN_01",
            "wnd[0]/usr/chkKNA1-STKZN",
        ):
            marcado = _set_checkbox(
                session,
                checkbox_id,
                selected=True,
                timeout=1,
                required=False,
            )
            if marcado is not None:
                break


def _preencher_dados_empresa(session, tipo_doc):
    _press(session, "wnd[0]/tbar[1]/btn[26]")

    prefixo = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
        "ssubSUBSC:SAPLATAB:0200/subAREA1:SAPMF02D:7211/"
    )

    _set_text(session, prefixo + "ctxtKNB1-AKONT", "11500700")
    _set_text(session, prefixo + "ctxtKNB1-FDGRV", _grupo_tesouraria(tipo_doc))

    # Dados de pagamento da área de empresa.
    # Mantém o fluxo padrão: preenche os campos e NÃO salva aqui,
    # porque o salvamento final continua sendo feito por _salvar_cliente_ou_setor().
    tab_pagamento = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB02"
    )
    wait_for_element(session, tab_pagamento, timeout=8).select()
    wait_until_ready(session)

    prefixo_pagamento_area1 = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB02/"
        "ssubSUBSC:SAPLATAB:0200/subAREA1:SAPMF02D:7215/"
    )
    prefixo_pagamento_area2 = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB02/"
        "ssubSUBSC:SAPLATAB:0200/subAREA2:SAPMF02D:7216/"
    )

    _set_text(session, prefixo_pagamento_area1 + "ctxtKNB1-ZTERM", "0001")
    _set_text(session, prefixo_pagamento_area2 + "ctxtKNB1-ZWELS", "A")
    banco = _set_text(session, prefixo_pagamento_area2 + "ctxtKNB1-HBKID", "BB100")

    if banco is not None:
        try:
            banco.setFocus()
        except Exception:
            try:
                banco.SetFocus()
            except Exception:
                pass

        try:
            banco.caretPosition = 5
        except Exception:
            pass

    wait_until_ready(session)


def _preencher_dados_vendas(session, setor, incluir_imposto=True):
    config = SETOR_CONFIG[setor]

    if element_exists(session, "wnd[0]/tbar[1]/btn[27]"):
        _press(session, "wnd[0]/tbar[1]/btn[27]")

    prefixo_tab1 = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
        "ssubSUBSC:SAPLATAB:0200/"
    )
    prefixo_area1 = prefixo_tab1 + "subAREA1:SAPMF02D:7310/"
    prefixo_area2 = prefixo_tab1 + "subAREA2:SAPMF02D:7311/"

    _set_text(session, prefixo_area1 + "ctxtKNVV-VKBUR", config["vendas"])
    _set_text(session, prefixo_area1 + "ctxtKNVV-VKGRP", config["grupo"])
    _set_text(session, prefixo_area2 + "ctxtKNVV-KALKS", "1")
    _set_text(session, prefixo_area2 + "ctxtKNVV-VERSG", "1")

    tab3 = "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB03"
    wait_for_element(session, tab3, timeout=8).select()
    wait_until_ready(session)

    prefixo_tab3 = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB03/"
        "ssubSUBSC:SAPLATAB:0200/"
    )

    _set_text(session, prefixo_tab3 + "subAREA3:SAPMF02D:7322/ctxtKNVV-KTGRD", "01")

    if incluir_imposto:
        _set_text(
            session,
            prefixo_tab3
            + "subAREA4:SAPMF02D:7323/subSUB_STEUER:SAPMF02D:7350/"
            "tblSAPMF02DTCTRL_STEUERN/ctxtKNVI-TAXKD[4,0]",
            "1",
            required=False,
        )


def _salvar_cliente_ou_setor(session):
    status_antes = ler_status_texto(session)
    _press(session, "wnd[0]/tbar[0]/btn[11]")
    _confirmar_popups_simples(session)
    wait_until_ready(session)

    status_depois = ler_status_texto(session)
    return status_depois or status_antes


def criar_cliente(session, dados, logger, progress_callback=None):
    try:
        cadastro = _normalizar_cadastro_cliente(dados)
        setores_requeridos = cadastro["setores"]
        setor_inicial = SETOR_INICIAL_CADASTRO

        logger.add(0, "Iniciando criacao de cliente no SAP.", publico=True)
        notificar_progresso(
            progress_callback,
            "XD01",
            "processando",
            "Criando cliente no SAP...",
            20,
        )

        _abrir_xd01(session, logger)
        _preencher_primeira_tela(
            session,
            cadastro["grupo_conta"],
            setor_inicial,
            incluir_empresa=True,
        )

        notificar_progresso(
            progress_callback,
            "XD01",
            "processando",
            "Preenchendo dados gerais do cliente...",
            42,
        )
        _preencher_dados_gerais(session, cadastro)
        _preencher_documentos_fiscais(session, cadastro)

        notificar_progresso(
            progress_callback,
            "XD01",
            "processando",
            "Preenchendo dados de empresa e vendas...",
            66,
        )
        _preencher_dados_empresa(session, cadastro["tipo_documento"])
        _preencher_dados_vendas(session, setor_inicial, incluir_imposto=True)

        status = _salvar_cliente_ou_setor(session)
        setores_criados = [setor_inicial]
        setores_pendentes = [
            setor
            for setor in setores_requeridos
            if setor and setor != setor_inicial
        ]

        if status:
            logger.add(0, f"Retorno SAP ao salvar cliente: {status}")

        logger.add(
            0,
            "Cliente salvo no XD01. O codigo SAP sera localizado pelo CPF/CNPJ no XD03.",
            publico=True,
        )

        notificar_progresso(
            progress_callback,
            "XD01",
            "concluido",
            "Cliente criado. Retomando busca pelo CPF/CNPJ no XD03...",
            100,
        )

        return resultado_padrao(
            ok=True,
            etapa="XD01",
            mensagem="Cliente criado com sucesso.",
            dados={
                "documento": cadastro["doc"],
                "tipo_documento": cadastro["tipo_documento"],
                "nome_cliente": " ".join(
                    parte for parte in (cadastro["nome1"], cadastro["nome2"]) if parte
                ).strip(),
                "setores_criados": setores_criados,
                "setores_pendentes": setores_pendentes,
            },
        )
    except Exception as exc:
        logger.add(0, f"Erro ao criar cliente: {exc}", nivel="ERRO", publico=True)
        notificar_progresso(
            progress_callback,
            "XD01",
            "erro",
            f"Falha ao criar cliente: {exc}",
            95,
        )
        return resultado_padrao(
            ok=False,
            etapa="XD01",
            mensagem="Erro ao criar cliente",
            erro_tecnico=str(exc),
        )


def adicionar_setores_cliente(
    session,
    dados,
    logger,
    progress_callback=None,
    abrir_nova_transacao=True,
):
    try:
        payload = dict(dados or {})
        cliente = str(payload.get("cliente") or "").strip()
        doc = limpar_doc(payload.get("doc") or payload.get("documento"))
        tipo_doc = payload.get("tipo_documento") or (tipo_documento(doc) if doc else "")
        grupo_conta = payload.get("grupo_conta") or (
            "PJ01" if tipo_doc == "cnpj" else "PF01" if tipo_doc == "cpf" else ""
        )
        setores = _ordenar_setores(
            payload.get("setores") or setores_necessarios_para_tipo(payload.get("tipo"))
        )

        if not cliente:
            raise ValueError("Numero do cliente SAP nao informado.")

        if not setores:
            raise ValueError("Nenhum setor informado para criacao.")

        logger.add(
            0,
            f"Adicionando setores ao cliente {cliente}: {', '.join(setores)}.",
            publico=True,
        )

        setores_criados = []
        setores_existentes = []

        for index, setor in enumerate(setores, start=1):
            if setor not in SETOR_CONFIG:
                raise ValueError(f"Setor nao mapeado: {setor}")

            notificar_progresso(
                progress_callback,
                "XD01",
                "processando",
                f"Criando setor {setor} para o cliente {cliente}...",
                min(95, 20 + index * 20),
            )

            try:
                if abrir_nova_transacao or index > 1:
                    _abrir_xd01(session, logger)

                _preencher_primeira_tela(
                    session,
                    grupo_conta,
                    setor,
                    cliente=cliente,
                    incluir_empresa=False,
                )
                _preencher_dados_vendas(session, setor, incluir_imposto=False)
                _salvar_cliente_ou_setor(session)
                setores_criados.append(setor)
            except Exception as exc:
                if not _erro_indica_setor_existente(session, exc):
                    raise

                setores_existentes.append(setor)
                logger.add(
                    0,
                    f"Setor {setor} ja existe para o cliente {cliente}; seguindo para o proximo setor.",
                    nivel="AVISO",
                    publico=True,
                )
                notificar_progresso(
                    progress_callback,
                    "XD01",
                    "processando",
                    f"Setor {setor} ja existe para o cliente {cliente}.",
                    min(95, 20 + index * 20),
                )
                _confirmar_popups_simples(session)

        partes_mensagem = []

        if setores_criados:
            partes_mensagem.append(f"criados: {', '.join(setores_criados)}")

        if setores_existentes:
            partes_mensagem.append(f"ja existiam: {', '.join(setores_existentes)}")

        mensagem_final = "; ".join(partes_mensagem) or "nenhum setor processado"
        notificar_progresso(
            progress_callback,
            "XD01",
            "concluido",
            f"Setores processados para o cliente {cliente}: {mensagem_final}.",
            100,
        )

        return resultado_padrao(
            ok=True,
            etapa="XD01",
            mensagem=(
                "Setores processados com aviso."
                if setores_existentes and not setores_criados
                else "Setores processados com sucesso."
            ),
            dados={
                "cliente": cliente,
                "documento": doc,
                "tipo_documento": tipo_doc,
                "setores_criados": setores_criados,
                "setores_existentes": setores_existentes,
            },
        )
    except Exception as exc:
        logger.add(0, f"Erro ao adicionar setores: {exc}", nivel="ERRO", publico=True)
        notificar_progresso(
            progress_callback,
            "XD01",
            "erro",
            f"Falha ao adicionar setores: {exc}",
            95,
        )
        return resultado_padrao(
            ok=False,
            etapa="XD01",
            mensagem="Erro ao adicionar setores",
            erro_tecnico=str(exc),
        )
