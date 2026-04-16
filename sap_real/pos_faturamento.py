import time
from datetime import datetime


# =========================
# ESPERA RÁPIDA
# =========================
def wait_for_element(session, element_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return session.findById(element_id)
        except:
            time.sleep(0.2)
    raise Exception(f"Elemento não encontrado: {element_id}")


# =========================
# RETRY INTELIGENTE
# =========================
def retry(func, tentativas=3):
    for i in range(tentativas):
        try:
            return func()
        except Exception as e:
            print(f"Tentativa {i+1} falhou: {e}")
            time.sleep(0.5)
    raise Exception("Falha após várias tentativas.")


# =========================
# FUNÇÃO PRINCIPAL
# =========================
def pos_faturamento(session):

    print("Iniciando pós faturamento...")

    # =========================
    # VF02 - CAPTURAR DOC
    # =========================
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVF02"
    session.findById("wnd[0]").sendVKey(0)

    campo_doc = wait_for_element(session, "wnd[0]/usr/ctxtVBRK-VBELN")
    doc_fat = campo_doc.text

    if not doc_fat:
        raise Exception("Documento de faturamento vazio.")

    print(f"Documento capturado: {doc_fat}")

    session.findById("wnd[0]").sendVKey(3)

    # =========================
    # FB03
    # =========================
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nFB03"
    session.findById("wnd[0]").sendVKey(0)

    # Inserir dados
    wait_for_element(session, "wnd[0]/usr/txtRF05L-BELNR").text = doc_fat
    session.findById("wnd[0]/usr/ctxtRF05L-BUKRS").text = "EMBA"
    session.findById("wnd[0]/usr/ctxtRF05L-BUKRS").caretPosition = 4
    session.findById("wnd[0]/usr/txtRF05L-GJAHR").text = datetime.now().strftime("%Y")

    session.findById("wnd[0]").sendVKey(0)

    # =========================
    # AJUSTAR GRID
    # =========================
    def ajustar_item():
        grid = wait_for_element(
            session,
            "wnd[0]/usr/cntlCTRL_CONTAINERBSEG/shellcont/shell"
        )

        grid.currentCellColumn = "KOBEZ"
        grid.doubleClickCurrentCell()

        session.findById("wnd[0]/tbar[1]/btn[25]").press()
        session.findById("wnd[0]/tbar[1]/btn[8]").press()

    retry(ajustar_item)

    # =========================
    # POPUP
    # =========================
    def tratar_popup():
        wait_for_element(session, "wnd[1]/usr/ctxtBSEG-HBKID").text = "BB100"
        session.findById("wnd[1]/usr/ctxtBSEG-ZLSCH").text = "A"
        session.findById("wnd[1]/tbar[0]/btn[0]").press()

    retry(tratar_popup)

    # =========================
    # SALVAR FB03
    # =========================
    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    session.findById("wnd[0]/tbar[0]/btn[15]").press()

    # =========================
    # VOLTAR VF02
    # =========================
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVF02"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, "wnd[0]/usr/ctxtVBRK-VBELN").text = doc_fat
    session.findById("wnd[0]").sendVKey(0)

    # =========================
    # AJUSTE FINAL VF02
    # =========================
    
    def ajustar_vf02():

    # =========================
    # ENTRAR NA TELA DE ITENS
    # =========================
     session.findById("wnd[0]/tbar[1]/btn[5]").press()

    # Espera grid carregar
    grid = wait_for_element(
        session,
        "wnd[0]/usr/tblSAPMV60ATCTRL_UEB_FAKT"
    )
    
    (ajustar_vf02)

    # =========================
    # SELECIONAR PRIMEIRA LINHA
    # =========================
    grid.getAbsoluteRow(0).selected = True

    campo_pos = session.findById(
        "wnd[0]/usr/tblSAPMV60ATCTRL_UEB_FAKT/ctxtVBRP-POSNR[0,0]"
    )

    campo_pos.setFocus()
    campo_pos.caretPosition = 0

    # =========================
    # SALVAR
    # =========================
    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    

    # =========================
    # VOLTAR
    # =========================
    session.findById("wnd[0]").sendVKey(3)
                           
    print("Pós faturamento finalizado com sucesso.")
    return doc_fat