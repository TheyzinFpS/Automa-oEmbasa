from datetime import datetime

from backend.flows.common import (
    aguardar_status_mudar,
    ler_status,
    ler_status_texto,
    notificar_progresso,
    resultado_padrao,
)
from backend.utils.sap_waits import wait_for_element
from backend.utils.timing import paced_sleep


_CAMPO_AUART = "wnd[0]/usr/ctxtVBAK-AUART"
_CAMPO_VKORG = "wnd[0]/usr/ctxtVBAK-VKORG"
_CAMPO_VTWEG = "wnd[0]/usr/ctxtVBAK-VTWEG"
_CAMPO_SPART = "wnd[0]/usr/ctxtVBAK-SPART"
_CAMPO_VKBUR = "wnd[0]/usr/ctxtVBAK-VKBUR"
_CAMPO_VKGRP = "wnd[0]/usr/ctxtVBAK-VKGRP"
_CAMPO_CLIENTE = (
    "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/"
    "subPART-SUB:SAPMV45A:4701/ctxtKUAGV-KUNNR"
)
_CAMPO_DESTINATARIO = (
    "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/"
    "subPART-SUB:SAPMV45A:4701/ctxtKUWEV-KUNNR"
)
_CAMPO_DATA_REFERENCIA = "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/ctxtVBKD-BSTDK"
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
_TREE_MENU = "wnd[0]/usr/cntlIMAGE_CONTAINER/shellcont/shell/shellcont[0]/shell"
_NODE_VA01 = "F00019"


_TIPOS_VA01 = {
    "viabilidade": {
        "material": "900000000032",
        "centro_lucro": "030002010L",
        "auart": "ZEST",
        "spart": "AE",
        "vkbur": "1055",
        "vkgrp": "DM",
        "descricao": "ANALISE DE VIABILIDADE TECNICA",
    },
    "agua": {
        "material": "900000000017",
        "centro_lucro": "030002010L",
        "auart": "ZPRO",
        "spart": "AG",
        "vkbur": "1055",
        "vkgrp": "DM",
        "descricao": "APROVACAO DE PROJETO DE ABASTECIMENTO DE AGUA",
    },
    "esgoto": {
        "material": "900000000018",
        "centro_lucro": "072002000L",
        "auart": "ZPRO",
        "spart": "EG",
        "vkbur": "1070",
        "vkgrp": "ME",
        "descricao": "APROVACAO DE PROJETO DE ESGOTAMENTO SANITARIO",
    },
}
def _normalizar_tipo(tipo):
    tipo_normalizado = str(tipo or "").strip().lower()
    if tipo_normalizado not in _TIPOS_VA01:
        raise ValueError(f"Tipo de solicitacao invalido para VA01: {tipo}")
    return tipo_normalizado


def _normalizar_endereco(dados):
    endereco = dict(dados.get("endereco") or {})
    cep = "".join(filter(str.isdigit, str(endereco.get("cep", ""))))

    return {
        "empreendimento": str(endereco.get("empreendimento", "")).strip(),
        "rua": str(endereco.get("rua", "")).strip(),
        "numero": str(endereco.get("numero", "")).strip() or "S/N",
        "bairro": str(endereco.get("bairro", "")).strip(),
        "complemento": str(endereco.get("complemento", "")).strip(),
        "cidade": str(endereco.get("cidade", "")).strip(),
        "estado": (str(endereco.get("estado", "")).strip().upper() or "BA"),
        "cep": cep,
    }


def _montar_texto(tipo, endereco):
    configuracao = _TIPOS_VA01[tipo]
    logradouro = f"{endereco['rua']}, {endereco['numero']}"

    if endereco["complemento"]:
        logradouro = f"{logradouro}, {endereco['complemento']}"

    return (
        f"Referente a solicitacao de {configuracao['descricao']}, "
        f"no EMPREENDIMENTO {endereco['empreendimento']}, localizado na "
        f"{logradouro}, bairro {endereco['bairro']}, "
        f"{endereco['cidade']}-{endereco['estado']}, CEP: {endereco['cep']}."
    )
def _pressionar_se_existir(session, element_id):
    try:
        session.findById(element_id).press()
        paced_sleep(0.2)
        return True
    except Exception:
        return False


def _fechar_wnd1_se_existir(session):
    try:
        session.findById("wnd[1]").close()
        paced_sleep(0.2)
        return True
    except Exception:
        return False


def _confirmar_popup_cancelamento(session):
    candidatos = (
        "wnd[1]/usr/btnSPOP-OPTION1",
        "wnd[1]/usr/btnSPOP-VAROPTION1",
        "wnd[1]/tbar[0]/btn[0]",
    )

    for element_id in candidatos:
        if _pressionar_se_existir(session, element_id):
            return True

    return False


def _esta_na_va01(session):
    try:
        wait_for_element(session, _CAMPO_AUART, timeout=1.2)
        return True
    except Exception:
        return False


def _limpar_contexto_antes_va01(session, logger=None):
    for _ in range(6):
        if _esta_na_va01(session):
            return

        houve_acao = False

        if _confirmar_popup_cancelamento(session):
            houve_acao = True

        if _fechar_wnd1_se_existir(session):
            houve_acao = True

        try:
            session.findById("wnd[0]").sendVKey(12)
            paced_sleep(0.2)
            houve_acao = True
        except Exception:
            pass

        if _confirmar_popup_cancelamento(session):
            houve_acao = True

        if not houve_acao:
            break

    if logger:
        logger.add(
            1,
            f"Status antes de abrir VA01: {ler_status_texto(session, status_bar_id=_STATUS_BAR)}",
        )


def _abrir_va01_via_comando(session):
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVA01"
    session.findById("wnd[0]").sendVKey(0)
    paced_sleep(0.5)
    _confirmar_popup_cancelamento(session)


def _abrir_va01_via_menu(session):
    session.findById("wnd[0]").maximize
    menu = session.findById(_TREE_MENU)
    menu.selectedNode = _NODE_VA01
    menu.doubleClickNode(_NODE_VA01)
    paced_sleep(0.5)
    _confirmar_popup_cancelamento(session)


def _abrir_va01(session, logger=None):
    _limpar_contexto_antes_va01(session, logger=logger)

    _abrir_va01_via_comando(session)
    if _esta_na_va01(session):
        return

    _limpar_contexto_antes_va01(session, logger=logger)

    _abrir_va01_via_menu(session)
    if _esta_na_va01(session):
        return

    status = ler_status_texto(session, status_bar_id=_STATUS_BAR)
    raise Exception(
        "Nao foi possivel abrir a VA01 apos a XD03. "
        f"Status SAP atual: {status or 'sem mensagem'}"
    )


def _preencher_cabecalho(session, configuracao):
    wait_for_element(session, _CAMPO_AUART)

    session.findById(_CAMPO_AUART).text = configuracao["auart"]
    session.findById(_CAMPO_VKORG).text = "EMBA"
    session.findById(_CAMPO_VTWEG).text = "PO"
    session.findById(_CAMPO_SPART).text = configuracao["spart"]
    session.findById(_CAMPO_VKBUR).text = configuracao["vkbur"]
    session.findById(_CAMPO_VKGRP).text = configuracao["vkgrp"]
    session.findById("wnd[0]").sendVKey(0)


def _preencher_cliente(session, codigo_cliente):
    wait_for_element(session, _CAMPO_CLIENTE)
    data_hoje = datetime.now().strftime("%d%m%Y")

    session.findById(_CAMPO_CLIENTE).text = codigo_cliente
    session.findById(_CAMPO_DESTINATARIO).text = codigo_cliente
    session.findById(_CAMPO_DATA_REFERENCIA).text = data_hoje
    session.findById("wnd[0]").sendVKey(0)


def _preencher_item_principal(session, configuracao):
    wait_for_element(session, _ABA_OVERVIEW).select()

    session.findById(_CAMPO_CENTRO).text = "CAB"
    session.findById(_CAMPO_CONDICAO_PAGAMENTO).text = "C060"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, _CAMPO_MATERIAL).text = configuracao["material"]
    session.findById("wnd[0]").sendVKey(0)

    session.findById(_CAMPO_QUANTIDADE).text = "1"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, _CAMPO_CENTRO_LUCRO).text = configuracao["centro_lucro"]
    session.findById("wnd[0]").sendVKey(0)
    paced_sleep(0.8)


def _preencher_texto_item(session, texto):
    session.findById("wnd[0]").sendVKey(2)
    wait_for_element(session, _ABA_TEXTO_ITEM).select()
    wait_for_element(session, _CAMPO_TEXTO_ITEM).text = texto + "\n"


def _preencher_condicoes(session, valor_sap):
    wait_for_element(session, _ABA_CONDICOES_ITEM).select()
    wait_for_element(session, _BOTAO_CONDICOES).press()
    wait_for_element(session, _TABELA_CONDICOES)

    session.findById(_CAMPO_TIPO_CONDICAO).text = "PR00"
    session.findById(_CAMPO_VALOR_CONDICAO).text = valor_sap
    session.findById("wnd[0]").sendVKey(0)


def _salvar_sem_captura(session):
    status_anterior, _ = ler_status(session, status_bar_id=_STATUS_BAR)

    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    paced_sleep(0.8)

    texto_status, tipo_status = aguardar_status_mudar(
        session,
        status_anterior,
        timeout=15,
        status_bar_id=_STATUS_BAR,
    )

    if tipo_status in {"E", "A"}:
        raise ValueError(texto_status or "SAP retornou erro ao salvar na VA01.")

    return texto_status or "Ordem criada com sucesso na VA01."


def _retornar_tela_inicial(session):
    for _ in range(2):
        try:
            session.findById("wnd[0]/tbar[0]/btn[12]").press()
            paced_sleep(0.3)
            _confirmar_popup_cancelamento(session)
        except Exception:
            break


def criar_pedido(session, dados, codigo_cliente, logger, progress_callback=None):
    progresso_atual = 6
    resultado_sucesso = None

    try:
        tipo = _normalizar_tipo(dados.get("tipo"))
        configuracao = _TIPOS_VA01[tipo]
        endereco = _normalizar_endereco(dados)

        valor_sap = (
            str((dados.get("valor_info") or {}).get("sap") or "").strip()
            or str(dados.get("valor", "")).replace("R$", "").strip()
        )

        texto_item = _montar_texto(tipo, endereco)

        logger.add(1, "Criando ordem na VA01...", publico=True)
        logger.add(1, f"Tipo VA01 selecionado: {tipo}")
        logger.add(1, f"Cliente aplicado na VA01: {codigo_cliente}")
        logger.add(1, f"Valor SAP aplicado na VA01: {valor_sap}")

        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Abrindo transacao VA01...",
            progresso_atual,
        )
        _abrir_va01(session, logger=logger)

        progresso_atual = 18
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Preenchendo cabecalho da ordem...",
            progresso_atual,
        )
        _preencher_cabecalho(session, configuracao)

        progresso_atual = 34
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Aplicando dados do cliente...",
            progresso_atual,
        )
        _preencher_cliente(session, codigo_cliente)

        progresso_atual = 54
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Configurando item principal...",
            progresso_atual,
        )
        _preencher_item_principal(session, configuracao)

        progresso_atual = 72
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Inserindo texto do empreendimento...",
            progresso_atual,
        )
        _preencher_texto_item(session, texto_item)

        progresso_atual = 86
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Aplicando condicao PR00...",
            progresso_atual,
        )
        _preencher_condicoes(session, valor_sap)

        progresso_atual = 96
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Salvando ordem na VA01...",
            progresso_atual,
        )
        status_sap = _salvar_sem_captura(session)

        logger.add(1, f"Retorno SAP VA01: {status_sap}")
        logger.add(1, "VA01 concluida com sucesso.", publico=True)

        progresso_atual = 99
        notificar_progresso(
            progress_callback,
            "VA01",
            "processando",
            "Retornando para a tela inicial...",
            progresso_atual,
        )
        _retornar_tela_inicial(session)

        notificar_progresso(
            progress_callback,
            "VA01",
            "concluido",
            "VA01 concluida com sucesso.",
            100,
        )

        resultado_sucesso = resultado_padrao(
            ok=True,
            etapa="VA01",
            mensagem="VA01 concluida com sucesso.",
            dados={
                "cliente": codigo_cliente,
                "tipo": tipo,
                "valor": valor_sap,
                "status_sap": status_sap,
            },
        )

    except Exception as e:
        logger.add(1, f"Erro VA01: {e}")
        notificar_progresso(
            progress_callback,
            "VA01",
            "erro",
            "Falha na VA01.",
            progresso_atual,
        )

        try:
            _limpar_contexto_antes_va01(session, logger=logger)
            _retornar_tela_inicial(session)
        except Exception:
            pass

        return resultado_padrao(
            ok=False,
            etapa="VA01",
            mensagem="Erro ao executar VA01.",
            erro_tecnico=str(e),
        )

    return resultado_sucesso
