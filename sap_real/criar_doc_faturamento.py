import time


# =========================
# ESPERA INTELIGENTE
# =========================
def wait_for_element(session, element_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return session.findById(element_id)
        except:
            time.sleep(0.1)
    raise Exception(f"Elemento não encontrado: {element_id}")


# =========================
# VF01 OTIMIZADO
# =========================
def criar_doc_faturamento(session):

    # =========================
    # ABRIR VF01
    # =========================
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVF01"
    session.findById("wnd[0]").sendVKey(0)

    # Espera tela carregar (campo padrão VF01)
    wait_for_element(session, "wnd[0]/usr")

    # =========================
    # SALVAR (GERAR FATURA)
    # =========================
    session.findById("wnd[0]").sendVKey(11)

    # Espera processamento (status muda ou tela reage)
    time.sleep(1.0)

    # =========================
    # VOLTAR
    # =========================
    session.findById("wnd[0]").sendVKey(3)

    print("Código do Doc.Fat criado")