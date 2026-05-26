import re

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


def setores_necessarios_para_tipo(tipo):
    tipo_normalizado = str(tipo or "").strip().lower()
    return TIPO_PARA_SETOR.get(tipo_normalizado, ())


def _extrair_numero_sap(texto):
    numeros = re.findall(r"\b\d{6,12}\b", str(texto or ""))
    return numeros[-1] if numeros else ""


def _limitar_texto(valor, limite):
    texto = str(valor or "").strip()
    return texto[: int(limite or 0)] if limite else texto


def _dividir_nome(nome, nome2="", limite=35):
    nome1 = str(nome or "").strip()
    complemento = str(nome2 or "").strip()

    if complemento:
        return _limitar_texto(nome1, limite), _limitar_texto(complemento, limite)

    if len(nome1) <= limite:
        return nome1, ""

    corte = nome1.rfind(" ", 0, limite + 1)
    if corte < 12:
        corte = limite

    return nome1[:corte].strip(), nome1[corte:].strip()[:limite]


def _normalizar_cadastro_cliente(dados):
    payload = dict(dados or {})
    doc = limpar_doc(payload.get("doc"))
    tipo_doc = tipo_documento(doc)
    tipo = str(payload.get("tipo") or "").strip().lower()
    setores = tuple(payload.get("setores") or setores_necessarios_para_tipo(tipo))

    if not setores:
        raise ValueError("Tipo de solicitacao sem setor SAP mapeado.")

    nome_base = (
        payload.get("nome1")
        or payload.get("razao_social")
        or payload.get("nome")
        or ""
    )
    nome1, nome2 = _dividir_nome(nome_base, payload.get("nome2"))

    endereco = payload.get("endereco") or {}
    rua = payload.get("rua") or endereco.get("rua")
    numero = payload.get("numero") or endereco.get("numero")
    bairro = payload.get("bairro") or endereco.get("bairro")
    cep = payload.get("cep") or endereco.get("cep")
    cidade = payload.get("cidade") or endereco.get("cidade")
    estado = (payload.get("estado") or endereco.get("estado") or "BA").upper()

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
        "titulo": payload.get("titulo") or ("Empresa" if tipo_doc == "cnpj" else ""),
        "nome1": nome1,
        "nome2": nome2,
        "sort1": _limitar_texto(payload.get("sort1") or nome1, 20),
        "sort2": _limitar_texto(payload.get("sort2") or nome2 or nome1, 20),
        "rua": _limitar_texto(rua, 60),
        "numero": _limitar_texto(numero, 10),
        "bairro": _limitar_texto(bairro, 40),
        "cep": str(cep or "").strip(),
        "cidade": _limitar_texto(cidade, 40).upper(),
        "estado": _limitar_texto(estado, 2),
        "telefone": _limitar_texto(payload.get("telefone") or "", 30),
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
            required=False,
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
        _set_text(session, prefixo + "txtKNA1-STCD1", dados["doc"])
    else:
        _set_text(session, prefixo + "txtKNA1-STCD2", dados["doc"], required=False)

    _set_text(
        session,
        prefixo + "txtKNA1-STCD3",
        dados["inscricao_estadual"],
        required=False,
    )


def _preencher_dados_empresa(session):
    _press(session, "wnd[0]/tbar[1]/btn[26]")

    prefixo = (
        "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
        "ssubSUBSC:SAPLATAB:0200/subAREA1:SAPMF02D:7211/"
    )

    _set_text(session, prefixo + "ctxtKNB1-AKONT", "11500700")
    _set_text(session, prefixo + "ctxtKNB1-FDGRV", "C-OUTRECPJ")


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
            "XD03",
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
            "XD03",
            "processando",
            "Preenchendo dados gerais do cliente...",
            42,
        )
        _preencher_dados_gerais(session, cadastro)
        _preencher_documentos_fiscais(session, cadastro)

        notificar_progresso(
            progress_callback,
            "XD03",
            "processando",
            "Preenchendo dados de empresa e vendas...",
            66,
        )
        _preencher_dados_empresa(session)
        _preencher_dados_vendas(session, setor_inicial, incluir_imposto=True)

        status = _salvar_cliente_ou_setor(session)
        cliente = _extrair_numero_sap(status)

        if not cliente:
            raise RuntimeError(
                "Cliente salvo, mas nao foi possivel capturar o numero SAP na barra de status."
            )

        setores_criados = [setor_inicial]
        setores_para_adicionar = [
            setor
            for setor in setores_requeridos
            if setor and setor != setor_inicial
        ]

        for setor in setores_para_adicionar:
            adicionar_setores_cliente(
                session,
                {
                    "cliente": cliente,
                    "doc": cadastro["doc"],
                    "tipo_documento": cadastro["tipo_documento"],
                    "setores": [setor],
                },
                logger,
                progress_callback=progress_callback,
                abrir_nova_transacao=True,
            )
            setores_criados.append(setor)

        notificar_progresso(
            progress_callback,
            "XD03",
            "concluido",
            f"Cliente {cliente} criado e preparado para o fluxo.",
            100,
        )

        return resultado_padrao(
            ok=True,
            etapa="XD03",
            mensagem="Cliente criado com sucesso.",
            dados={
                "cliente": cliente,
                "documento": cadastro["doc"],
                "tipo_documento": cadastro["tipo_documento"],
                "nome_cliente": " ".join(
                    parte for parte in (cadastro["nome1"], cadastro["nome2"]) if parte
                ).strip(),
                "setores_criados": setores_criados,
            },
        )
    except Exception as exc:
        logger.add(0, f"Erro ao criar cliente: {exc}", nivel="ERRO", publico=True)
        notificar_progresso(
            progress_callback,
            "XD03",
            "erro",
            f"Falha ao criar cliente: {exc}",
            95,
        )
        return resultado_padrao(
            ok=False,
            etapa="XD03",
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
        tipo_doc = payload.get("tipo_documento") or (tipo_documento(doc) if doc else "cnpj")
        grupo_conta = payload.get("grupo_conta") or ("PJ01" if tipo_doc == "cnpj" else "PF01")
        setores = tuple(payload.get("setores") or setores_necessarios_para_tipo(payload.get("tipo")))

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

        for index, setor in enumerate(setores, start=1):
            if setor not in SETOR_CONFIG:
                raise ValueError(f"Setor nao mapeado: {setor}")

            notificar_progresso(
                progress_callback,
                "XD03",
                "processando",
                f"Criando setor {setor} para o cliente {cliente}...",
                min(95, 20 + index * 20),
            )

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

        notificar_progresso(
            progress_callback,
            "XD03",
            "concluido",
            f"Setores criados para o cliente {cliente}: {', '.join(setores_criados)}.",
            100,
        )

        return resultado_padrao(
            ok=True,
            etapa="XD03",
            mensagem="Setores criados com sucesso.",
            dados={
                "cliente": cliente,
                "documento": doc,
                "tipo_documento": tipo_doc,
                "setores_criados": setores_criados,
            },
        )
    except Exception as exc:
        logger.add(0, f"Erro ao adicionar setores: {exc}", nivel="ERRO", publico=True)
        notificar_progresso(
            progress_callback,
            "XD03",
            "erro",
            f"Falha ao adicionar setores: {exc}",
            95,
        )
        return resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Erro ao adicionar setores",
            erro_tecnico=str(exc),
        )
