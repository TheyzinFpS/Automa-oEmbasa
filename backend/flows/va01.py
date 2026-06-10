import time
from datetime import datetime

from backend.flows.multa_contratual import (
    TIPO_MULTA_CONTRATUAL,
    montar_texto_multa_contratual,
)
from backend.utils.sap_waits import wait_for_element


_CAMPO_TIPO_ORDEM = "wnd[0]/usr/ctxtVBAK-AUART"
_CAMPO_ORG_VENDAS = "wnd[0]/usr/ctxtVBAK-VKORG"
_CAMPO_CANAL = "wnd[0]/usr/ctxtVBAK-VTWEG"
_CAMPO_SETOR = "wnd[0]/usr/ctxtVBAK-SPART"
_CAMPO_ESCRITORIO = "wnd[0]/usr/ctxtVBAK-VKBUR"
_CAMPO_EQUIPE_VENDAS = "wnd[0]/usr/ctxtVBAK-VKGRP"

_CAMPO_DATA_REFERENCIA = "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/ctxtVBKD-BSTDK"
_CAMPO_CLIENTE = (
    "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/"
    "subPART-SUB:SAPMV45A:4701/ctxtKUAGV-KUNNR"
)
_CAMPO_DESTINATARIO = (
    "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/"
    "subPART-SUB:SAPMV45A:4701/ctxtKUWEV-KUNNR"
)

_ABA_OVERVIEW = "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01"
_CAMPO_CENTRO = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
    "ssubSUBSCREEN_BODY:SAPMV45A:4400/"
    "ssubHEADER_FRAME:SAPMV45A:4440/ctxtRV45A-DWERK"
)
_CAMPO_CONDICAO_PAGAMENTO = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
    "ssubSUBSCREEN_BODY:SAPMV45A:4400/"
    "ssubHEADER_FRAME:SAPMV45A:4440/ctxtVBKD-ZTERM"
)
_CAMPO_MATERIAL = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
    "ssubSUBSCREEN_BODY:SAPMV45A:4400/subSUBSCREEN_TC:SAPMV45A:4900/"
    "tblSAPMV45ATCTRL_U_ERF_AUFTRAG/ctxtRV45A-MABNR[1,0]"
)
_CAMPO_QUANTIDADE = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
    "ssubSUBSCREEN_BODY:SAPMV45A:4400/subSUBSCREEN_TC:SAPMV45A:4900/"
    "tblSAPMV45ATCTRL_U_ERF_AUFTRAG/txtRV45A-KWMENG[2,0]"
)
_CAMPO_CENTRO_LUCRO = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
    "ssubSUBSCREEN_BODY:SAPMV45A:4400/subSUBSCREEN_TC:SAPMV45A:4900/"
    "tblSAPMV45ATCTRL_U_ERF_AUFTRAG/ctxtVBAP-PRCTR[53,0]"
)

_ABA_TEXTO_ITEM = "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\10"
_CAMPO_TEXTO_ITEM = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\10/"
    "ssubSUBSCREEN_BODY:SAPMV45A:4152/subSUBSCREEN_TEXT:SAPLV70T:2100/"
    "cntlSPLITTER_CONTAINER/shellcont/shellcont/shell/shellcont[1]/shell"
)

_ABA_CONDICOES_ITEM = "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06"
_BOTAO_CONDICOES = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
    "ssubSUBSCREEN_BODY:SAPLV69A:6201/"
    "subSUBSCREEN_PUSHBUTTONS:SAPLV69A:1000/btnBT_KOAN"
)
_TABELA_CONDICOES = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
    "ssubSUBSCREEN_BODY:SAPLV69A:6201/tblSAPLV69ATCTRL_KONDITIONEN"
)
_CAMPO_TIPO_CONDICAO = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
    "ssubSUBSCREEN_BODY:SAPLV69A:6201/tblSAPLV69ATCTRL_KONDITIONEN/"
    "ctxtKOMV-KSCHL[1,1]"
)
_CAMPO_VALOR_CONDICAO = (
    "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
    "ssubSUBSCREEN_BODY:SAPLV69A:6201/tblSAPLV69ATCTRL_KONDITIONEN/"
    "txtKOMV-KBETR[3,1]"
)

_STATUS_BAR = "wnd[0]/sbar"


_TIPOS_VA01 = {
    "viabilidade": {
        "tipo_ordem": "ZEST",
        "canal": "PO",
        "setor": "AE",
        "escritorio": "1055",
        "equipe": "DM",
        "centro": "CAB",
        "condicao_pagamento": "C060",
        "material": "900000000032",
        "centro_lucro": "030002010L",
        "descricao": "ANÁLISE DE VIABILIDADE TÉCNICA",
    },
    "agua": {
        "tipo_ordem": "ZPRO",
        "canal": "PO",
        "setor": "AG",
        "escritorio": "1055",
        "equipe": "DM",
        "centro": "CAB",
        "condicao_pagamento": "C060",
        "material": "900000000017",
        "centro_lucro": "030002010L",
        "descricao": "APROVAÇÃO DE PROJETO DE ABASTECIMENTO DE ÁGUA",
    },
    "esgoto": {
        "tipo_ordem": "ZPRO",
        "canal": "PO",
        "setor": "EG",
        "escritorio": "1070",
        "equipe": "ME",
        "centro": "CAB",
        "condicao_pagamento": "C060",
        "material": "900000000018",
        "centro_lucro": "072002000L",
        "descricao": "APROVAÇÃO DE PROJETO DE ESGOTAMENTO SANITÁRIO",
    },
    TIPO_MULTA_CONTRATUAL: {
        "tipo_ordem": "ZMTC",
        "canal": "MC",
        "setor": "MC",
        "escritorio": "1010",
        "equipe": "CAB",
        "centro": "CAB",
        "condicao_pagamento": "C030",
        "material": "900000000052",
        "centro_lucro": "030002010L",
        "descricao": "MULTA CONTRATUAL",
    },
}


def resultado_padrao(ok, etapa, mensagem, dados=None, erro_tecnico=None):
    return {
        "ok": ok,
        "etapa": etapa,
        "mensagem": mensagem,
        "dados": dados,
        "erro_tecnico": erro_tecnico,
    }


def _notificar(progress_callback, status, mensagem=None, percentual=None):
    if not callable(progress_callback):
        return
    try:
        progress_callback("VA01", status, mensagem, percentual)
    except Exception:
        return


def _normalizar_tipo(tipo):
    tipo_normalizado = str(tipo or "").strip().lower()
    if tipo_normalizado not in _TIPOS_VA01:
        raise ValueError(f"Tipo de solicitação inválido para VA01: {tipo}")
    return tipo_normalizado


def _resolver_condicao_pagamento(tipo, dados, configuracao):
    if tipo == TIPO_MULTA_CONTRATUAL:
        validade = "".join(filter(str.isdigit, str(dados.get("validade_dias_uteis", ""))))
        return "C060" if validade == "60" else "C030"

    return configuracao.get("condicao_pagamento", "C060")


def _normalizar_endereco(dados):
    endereco = dict(dados.get("endereco") or {})
    cep_original = str(endereco.get("cep", "")).strip().upper()
    sem_cep = bool(endereco.get("sem_cep")) or cep_original in {
        "SEM CEP",
        "SEM-CEP",
        "S/CEP",
    }
    cep_digitos = "".join(filter(str.isdigit, cep_original))
    cep = "SEM CEP"

    if not sem_cep and len(cep_digitos) == 8:
        cep = f"{cep_digitos[:5]}-{cep_digitos[5:]}"

    return {
        "empreendimento": str(endereco.get("empreendimento", "")).strip().upper(),
        "rua": str(endereco.get("rua", "")).strip().upper(),
        "numero": str(endereco.get("numero", "")).strip().upper() or "S/N",
        "bairro": str(endereco.get("bairro", "")).strip().upper(),
        "complemento": str(endereco.get("complemento", "")).strip().upper(),
        "cidade": str(endereco.get("cidade", "")).strip().upper(),
        "estado": str(endereco.get("estado", "")).strip().upper() or "BA",
        "cep": cep,
    }


def _montar_texto(tipo, endereco, dados=None):
    if tipo == TIPO_MULTA_CONTRATUAL:
        return montar_texto_multa_contratual(dados or {})

    configuracao = _TIPOS_VA01[tipo]
    logradouro = f"{endereco['rua']}, {endereco['numero']}"

    if endereco["complemento"]:
        logradouro = f"{logradouro}, {endereco['complemento']}"

    return (
        f"Referente à solicitação de {configuracao['descricao']}, "
        f"no empreendimento {endereco['empreendimento']}, localizado na "
        f"{logradouro}, bairro {endereco['bairro']}, "
        f"{endereco['cidade']}-{endereco['estado']}, CEP: {endereco['cep']}."
    )


def _ler_propriedade(componente, *nomes):
    for nome in nomes:
        try:
            valor = getattr(componente, nome)
        except Exception:
            continue

        if valor is not None:
            return str(valor)

    return ""


def _ler_status(session):
    status_bar = wait_for_element(session, _STATUS_BAR, timeout=3)
    texto = _ler_propriedade(status_bar, "Text", "text").strip()
    tipo = _ler_propriedade(status_bar, "MessageType", "messageType").strip().upper()
    return texto, tipo


def _aguardar_novo_status(session, texto_anterior="", timeout=12):
    inicio = time.monotonic()
    ultimo_texto = texto_anterior
    ultimo_tipo = ""

    while time.monotonic() - inicio < timeout:
        try:
            texto_atual, tipo_atual = _ler_status(session)
        except Exception:
            time.sleep(0.1)
            continue

        if texto_atual and texto_atual != texto_anterior:
            return texto_atual, tipo_atual

        if texto_atual:
            ultimo_texto = texto_atual
            ultimo_tipo = tipo_atual

        time.sleep(0.1)

    return ultimo_texto, ultimo_tipo


def _pressionar_se_existir(session, element_id):
    try:
        session.findById(element_id).press()
        return True
    except Exception:
        return False


def _confirmar_popup_cancelamento(session):
    for element_id in (
        "wnd[1]/usr/btnSPOP-OPTION1",
        "wnd[1]/usr/btnSPOP-VAROPTION1",
        "wnd[1]/tbar[0]/btn[0]",
    ):
        if _pressionar_se_existir(session, element_id):
            return True

    return False


def _abrir_va01(session, configuracao):
    session.findById("wnd[0]").maximize()
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVA01"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, _CAMPO_TIPO_ORDEM, timeout=10).text = configuracao["tipo_ordem"]
    wait_for_element(session, _CAMPO_ORG_VENDAS, timeout=10).text = "EMBA"
    wait_for_element(session, _CAMPO_CANAL, timeout=10).text = configuracao.get("canal", "PO")
    wait_for_element(session, _CAMPO_SETOR, timeout=10).text = configuracao["setor"]
    wait_for_element(session, _CAMPO_ESCRITORIO, timeout=10).text = configuracao["escritorio"]

    campo_equipe = wait_for_element(session, _CAMPO_EQUIPE_VENDAS, timeout=10)
    campo_equipe.text = configuracao["equipe"]
    campo_equipe.setFocus()
    campo_equipe.caretPosition = len(configuracao["equipe"])

    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, _CAMPO_DATA_REFERENCIA, timeout=10)


def _preencher_dados_iniciais(session, codigo_cliente):
    data_hoje = datetime.now().strftime("%d%m%Y")

    wait_for_element(session, _CAMPO_DATA_REFERENCIA, timeout=10).text = data_hoje
    wait_for_element(session, _CAMPO_CLIENTE, timeout=10).text = str(codigo_cliente).strip()
    wait_for_element(session, _CAMPO_DESTINATARIO, timeout=10).text = str(codigo_cliente).strip()


def _preencher_item_principal(session, configuracao, condicao_pagamento=None):
    wait_for_element(session, _ABA_OVERVIEW, timeout=10).select()

    campo_centro = wait_for_element(session, _CAMPO_CENTRO, timeout=10)
    campo_centro.text = configuracao.get("centro", "CAB")

    campo_pagamento = wait_for_element(session, _CAMPO_CONDICAO_PAGAMENTO, timeout=10)
    campo_pagamento.text = condicao_pagamento or configuracao.get("condicao_pagamento", "C060")

    campo_material = wait_for_element(session, _CAMPO_MATERIAL, timeout=10)
    campo_material.text = configuracao["material"]
    campo_material.setFocus()
    campo_material.caretPosition = len(configuracao["material"])

    session.findById("wnd[0]").sendVKey(0)

    try:
        campo_qtd = wait_for_element(session, _CAMPO_QUANTIDADE, timeout=5)
        campo_qtd.text = "1"
        session.findById("wnd[0]").sendVKey(0)
    except Exception:
        pass

    try:
        campo_prctr = wait_for_element(session, _CAMPO_CENTRO_LUCRO, timeout=5)
        campo_prctr.text = configuracao["centro_lucro"]
        session.findById("wnd[0]").sendVKey(0)
    except Exception:
        pass


def _preencher_texto_item(session, texto):
    session.findById("wnd[0]").sendVKey(2)
    wait_for_element(session, _ABA_TEXTO_ITEM, timeout=10).select()
    wait_for_element(session, _CAMPO_TEXTO_ITEM, timeout=10).text = texto + "\n"


def _preencher_condicoes(session, valor_sap):
    wait_for_element(session, _ABA_CONDICOES_ITEM, timeout=10).select()
    wait_for_element(session, _BOTAO_CONDICOES, timeout=10).press()
    wait_for_element(session, _TABELA_CONDICOES, timeout=10)

    wait_for_element(session, _CAMPO_TIPO_CONDICAO, timeout=10).text = "PR00"
    wait_for_element(session, _CAMPO_VALOR_CONDICAO, timeout=10).text = valor_sap
    session.findById("wnd[0]").sendVKey(0)


def _salvar_sem_captura(session):
    status_anterior, _ = _ler_status(session)

    session.findById("wnd[0]/tbar[0]/btn[11]").press()

    texto_status, tipo_status = _aguardar_novo_status(
        session,
        status_anterior,
        timeout=15,
    )

    if tipo_status in {"E", "A"}:
        raise ValueError(texto_status or "SAP retornou erro ao salvar na VA01.")

    return texto_status or "Ordem criada com sucesso na VA01."


def _retornar_tela_inicial(session):
    for _ in range(2):
        try:
            session.findById("wnd[0]/tbar[0]/btn[12]").press()
            _confirmar_popup_cancelamento(session)
        except Exception:
            break


def criar_pedido(session, dados, codigo_cliente, logger, progress_callback=None):
    progresso_atual = 6

    try:
        tipo = _normalizar_tipo(dados.get("tipo"))
        configuracao = _TIPOS_VA01[tipo]
        condicao_pagamento = _resolver_condicao_pagamento(tipo, dados, configuracao)
        endereco = _normalizar_endereco(dados)

        valor_sap = (
            str((dados.get("valor_info") or {}).get("sap") or "").strip()
            or str(dados.get("valor", "")).replace("R$", "").strip()
        )

        texto_item = _montar_texto(tipo, endereco, dados=dados)

        logger.add(1, "Criando ordem na VA01...", publico=True)
        logger.add(1, f"Tipo VA01 selecionado: {tipo}")
        logger.add(1, f"Cliente aplicado na VA01: {codigo_cliente}")
        logger.add(1, f"Valor SAP aplicado na VA01: {valor_sap}")
        logger.add(1, f"Condicao de pagamento aplicada na VA01: {condicao_pagamento}")

        progresso_atual = 10
        _notificar(
            progress_callback,
            "processando",
            "Abrindo transação VA01 e preenchendo tela inicial...",
            progresso_atual,
        )
        _abrir_va01(session, configuracao)

        progresso_atual = 30
        _notificar(
            progress_callback,
            "processando",
            "Preenchendo cliente e data...",
            progresso_atual,
        )
        _preencher_dados_iniciais(session, codigo_cliente)

        progresso_atual = 55
        _notificar(
            progress_callback,
            "processando",
            "Preenchendo centro, pagamento e material...",
            progresso_atual,
        )
        _preencher_item_principal(session, configuracao, condicao_pagamento)

        progresso_atual = 72
        _notificar(
            progress_callback,
            "processando",
            "Inserindo texto do pedido...",
            progresso_atual,
        )
        _preencher_texto_item(session, texto_item)

        progresso_atual = 86
        _notificar(
            progress_callback,
            "processando",
            "Aplicando condicao PR00...",
            progresso_atual,
        )
        _preencher_condicoes(session, valor_sap)

        progresso_atual = 96
        _notificar(
            progress_callback,
            "processando",
            "Salvando ordem na VA01...",
            progresso_atual,
        )
        status_sap = _salvar_sem_captura(session)

        logger.add(1, f"Retorno SAP VA01: {status_sap}")
        logger.add(1, "VA01 concluída com sucesso.", publico=True)

        progresso_atual = 99
        _notificar(
            progress_callback,
            "processando",
            "Retornando para a tela inicial...",
            progresso_atual,
        )
        _retornar_tela_inicial(session)

        _notificar(progress_callback, "concluido", "VA01 concluída com sucesso.", 100)

        return resultado_padrao(
            ok=True,
            etapa="VA01",
            mensagem="VA01 concluída com sucesso.",
            dados={
                "cliente": codigo_cliente,
                "tipo": tipo,
                "valor": valor_sap,
                "status_sap": status_sap,
            },
        )

    except Exception as e:
        logger.add(1, f"Erro VA01: {e}", nivel="ERRO")
        _notificar(progress_callback, "erro", "Falha na VA01.", progresso_atual)

        try:
            _retornar_tela_inicial(session)
        except Exception:
            pass

        return resultado_padrao(
            ok=False,
            etapa="VA01",
            mensagem="Erro ao executar VA01.",
            erro_tecnico=str(e),
        )
