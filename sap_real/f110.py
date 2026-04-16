import time
from datetime import datetime, timedelta
import win32com.client

# =========================
# CONEXÃO SAP
# =========================
SapGuiAuto = win32com.client.GetObject("SAPGUI")
application = SapGuiAuto.GetScriptingEngine
connection = application.Children(0)
session = connection.Children(0)

# =========================
# UTILS
# =========================

def wait_for_element(session, element_id, timeout=10):
    for _ in range(timeout * 2):
        try:
            return session.findById(element_id)
        except:
            time.sleep(0.5)
    raise Exception(f"Elemento não encontrado: {element_id}")


def safe_find(session, element_id):
    try:
        return session.findById(element_id)
    except:
        return None


def ultimo_dia_mes():
    hoje = datetime.now()
    prox_mes = hoje.replace(day=28) + timedelta(days=4)
    ultimo = prox_mes - timedelta(days=prox_mes.day)
    return ultimo.strftime("%d%m%Y")


# =========================== #
# GERAÇÃO INTELIGENTE DE BOL  #
# =========================== #

def gerar_identificacao(session, data_exec):

    for i in range(1, 100):
        ident = f"BOL{i:02d}"

        wait_for_element(session, "wnd[0]/usr/ctxtF110V-LAUFD").text = data_exec
        session.findById("wnd[0]/usr/ctxtF110V-LAUFI").text = ident
        session.findById("wnd[0]").sendVKey(0)

        time.sleep(1)

        # VALIDA PARÂMETRO
        try:
            wait_for_element(session, "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR").select()

            campo_cliente = wait_for_element(
                session,
                "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/"
                "ssubSUBSCREEN_BODY:SAPF110V:0202/"
                "subSUBSCR_SEL:SAPF110V:7004/ctxtR_KUNNR-LOW"
            )

            if campo_cliente.text.strip() != "":
                session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpSTA").select()
                continue

        except:
            pass

        # VALIDA LOG
        try:
            session.findById("wnd[0]/tbar[1]/btn[20]").press()
            popup = safe_find(session, "wnd[1]")
            if popup:
                popup.findById("tbar[0]/btn[12]").press()
            continue
        except:
            return ident

    raise Exception("Nenhuma identificação disponível")


# =========================
# SELEÇÃO LIVRE VALIDADA
# =========================

def preencher_selecao_livre(session, doc_formatado):

    wait_for_element(session, "wnd[0]/usr/tabsF110_TABSTRIP/tabpSEL").select()

    for tentativa in range(2):

        session.findById("wnd[0]").sendVKey(4)
        time.sleep(1)

        try:
            session.findById("wnd[1]/tbar[0]/btn[0]").press()
        except:
            pass

        campo = wait_for_element(
            session,
            "wnd[0]/usr/tabsF110_TABSTRIP/tabpSEL/"
            "ssubSUBSCREEN_BODY:SAPF110V:0203/"
            "sub:SAPF110V:0203/txtF110V-LIST1[1,11]"
        )

        campo.text = doc_formatado
        session.findById("wnd[0]").sendVKey(0)

        time.sleep(1)

        if campo.text.strip() == doc_formatado:
            print("Seleção livre OK ✅")
            return

    raise Exception("Erro na seleção livre ❌")


# =========================
# LOG VALIDADO
# =========================

def configurar_log(session, cliente):

    wait_for_element(session, "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG").select()

    chk1 = session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/ssubSUBSCREEN_BODY:SAPF110V:0204/chkF110V-XTRFA")
    chk2 = session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/ssubSUBSCREEN_BODY:SAPF110V:0204/chkF110V-XTRZE")
    chk3 = session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/ssubSUBSCREEN_BODY:SAPF110V:0204/chkF110V-XTRBL")

    chk1.selected = True
    chk2.selected = True
    chk3.selected = True

    campo_vonkd = session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/ssubSUBSCREEN_BODY:SAPF110V:0204/sub:SAPF110V:0204/txtF110V-VONKD[0,23]")
    campo_biskd = session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/ssubSUBSCREEN_BODY:SAPF110V:0204/sub:SAPF110V:0204/txtF110V-BISKD[0,34]")

    campo_vonkd.text = cliente
    campo_biskd.text = cliente

    time.sleep(1)

    if not (chk1.selected and chk2.selected and chk3.selected):
        raise Exception("Erro LOG checkboxes ❌")

    if campo_vonkd.text.strip() != cliente or campo_biskd.text.strip() != cliente:
        raise Exception("Erro cliente LOG ❌")

    print("LOG OK ✅")


# =========================
# STATUS
# =========================

def tratar_popups_status(session):

    wait_for_element(session, "wnd[0]/usr/tabsF110_TABSTRIP/tabpSTA").select()
    time.sleep(1)

    try:
        wait_for_element(session, "wnd[1]").findById("usr/btnSPOP-OPTION1").press()
    except:
        pass

    time.sleep(1)

    try:
        wait_for_element(session, "wnd[1]").findById("tbar[0]/btn[0]").press()
    except:
        pass

    time.sleep(1)

    session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpSTA").select()

    try:
        wait_for_element(session, "wnd[1]").findById("usr/btnSPOP-OPTION1").press()
    except:
        pass


# =========================
# PROPOSTA
# =========================

def executar_proposta(session):

    wait_for_element(session, "wnd[0]/tbar[1]/btn[13]").press()
    popup = wait_for_element(session, "wnd[1]")

    popup.findById("usr/chkF110V-XSTRF").selected = True
    popup.findById("tbar[0]/btn[0]").press()

    session.findById("wnd[0]").sendVKey(0)


# =========================
# PAGAMENTO
# =========================

def executar_pagamento(session):

    wait_for_element(session, "wnd[0]/tbar[1]/btn[7]").press()
    popup = wait_for_element(session, "wnd[1]")

    popup.findById("usr/chkF110V-XMITD").selected = True
    popup.findById("tbar[0]/btn[0]").press()

    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)


# =========================
# F110
# =========================

def f110(session, cliente, doc_fat):

    data_exec = datetime.now().strftime("%d%m%Y")
    data_lanc = ultimo_dia_mes()
    doc_formatado = f"00{doc_fat}"

    wait_for_element(session, "wnd[0]").maximize()

    session.findById(
        "wnd[0]/usr/cntlIMAGE_CONTAINER/shellcont/shell/shellcont[0]/shell"
    ).doubleClickNode("F00024")

    time.sleep(2)

    gerar_identificacao(session, data_exec)

    # PARÂMETROS
    wait_for_element(session, "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR").select()

    session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/ssubSUBSCREEN_BODY:SAPF110V:0202/txtF110V-BUKLS[0,0]").text = "EMBA"
    session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/ssubSUBSCREEN_BODY:SAPF110V:0202/ctxtF110V-ZWELS[1,0]").text = "A"
    session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/ssubSUBSCREEN_BODY:SAPF110V:0202/ctxtF110V-NEDAT[2,0]").text = data_lanc
    session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/subSUBSCR_SEL:SAPF110V:7004/ctxtR_KUNNR-LOW").text = cliente

    # SELEÇÃO LIVRE
    preencher_selecao_livre(session, doc_formatado)

    # LOG
    configurar_log(session, cliente)

    # IMPRESSÃO
    wait_for_element(session, "wnd[0]/usr/tabsF110_TABSTRIP/tabpPRI").select()
    session.findById("wnd[0]/usr/tabsF110_TABSTRIP/tabpPRI/ssubSUBSCREEN_BODY:SAPF110V:0205/tblSAPF110VCTRL_DRPTAB/ctxtF110V-VARI1[1,2]").text = "BB_BOLETO_REC"

    # STATUS
    tratar_popups_status(session)

    # PROPOSTA
    executar_proposta(session)

    # PAGAMENTO
    executar_pagamento(session)

    print("F110 finalizado com sucesso 🚀")