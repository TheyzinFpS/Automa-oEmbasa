import time

# =========================
# CAMPOS E IDs FIXOS
# =========================
_CAMPO_CNPJ = "wnd[2]/usr/tabsG_SELONETABSTRIP/tabpTAB006/ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/txtG_SELFLD_TAB-LOW[0,24]"
_CAMPO_CPF  = "wnd[2]/usr/tabsG_SELONETABSTRIP/tabpTAB006/ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/txtG_SELFLD_TAB-LOW[1,24]"
_CAMPO_CLIENTE = "wnd[1]/usr/ctxtRF02D-KUNNR"


# =========================
# ESPERA INTELIGENTE
# =========================
def wait_for_element(session, element_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return session.findById(element_id)
        except Exception:
            time.sleep(0.2)
    raise Exception(f"Elemento não encontrado: {element_id}")


# =========================
# LIMPAR CPF/CNPJ
# =========================
def limpar_doc(doc):
    return "".join(filter(str.isdigit, doc))


# =========================
# IDENTIFICAR TIPO
# =========================
def tipo_documento(doc):
    if len(doc) == 11:
        return "cpf"
    elif len(doc) == 14:
        return "cnpj"
    raise ValueError(
        f"Documento inválido: esperado 11 (CPF) ou 14 (CNPJ), recebido {len(doc)}"
    )


# =========================
# HELPERS INTERNOS
# =========================
def _campo_ainda_tem_doc(session, campo, doc):
    try:
        return session.findById(campo).text.strip() == doc
    except:
        return False


def _ler_codigo_cliente(session, tipo, doc):
    campo_cliente = wait_for_element(session, _CAMPO_CLIENTE)
    codigo = campo_cliente.text.strip()
    if not codigo:
        raise ValueError(f"Código vazio para {tipo.upper()}: {doc}")
    print(f"✅ Cliente encontrado ({tipo.upper()}): {codigo}")
    return codigo


# =========================
# BUSCAR CLIENTE — CNPJ
# =========================
def _buscar_por_cnpj(session, doc):
    elemento = wait_for_element(session, _CAMPO_CNPJ)
    elemento.text = doc
    session.findById("wnd[2]").sendVKey(0)
    time.sleep(1)

    if _campo_ainda_tem_doc(session, _CAMPO_CNPJ, doc):
        print(f"❌ CNPJ não cadastrado: {doc}")
        session.findById("wnd[2]").sendVKey(12)
        time.sleep(0.3)
        session.findById("wnd[1]").sendVKey(12)
        return None

    codigo = _ler_codigo_cliente(session, "cnpj", doc)
    session.findById("wnd[1]").sendVKey(0)
    time.sleep(1)
    session.findById("wnd[1]").sendVKey(12)
    wait_for_element(session, "wnd[0]/usr")
    return codigo


# =========================
# BUSCAR CLIENTE — CPF
# =========================
def _buscar_por_cpf(session, doc):
    elemento = wait_for_element(session, _CAMPO_CPF)
    elemento.text = doc
    elemento.setFocus()
    elemento.caretPosition = len(doc)
    session.findById("wnd[2]/tbar[0]/btn[0]").press()
    time.sleep(1)

    if _campo_ainda_tem_doc(session, _CAMPO_CPF, doc):
        print(f"❌ CPF não cadastrado: {doc}")
        session.findById("wnd[2]/tbar[0]/btn[12]").press()
        time.sleep(0.3)
        session.findById("wnd[1]/tbar[0]/btn[12]").press()
        return None

    session.findById("wnd[2]").sendVKey(0)
    time.sleep(0.5)

    codigo = _ler_codigo_cliente(session, "cpf", doc)
    session.findById("wnd[1]/tbar[0]/btn[12]").press()
    wait_for_element(session, "wnd[0]/usr")
    return codigo


# =========================
# BUSCAR CLIENTE (ENTRADA)
# =========================
def buscar_cliente(session, doc):
    doc  = limpar_doc(doc)
    tipo = tipo_documento(doc)

    session.findById("wnd[0]").maximize()
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nXD03"
    session.findById("wnd[0]").sendVKey(0)
    wait_for_element(session, "wnd[0]/usr")

    session.findById("wnd[1]").sendVKey(4)
    wait_for_element(session, "wnd[2]")

    return _buscar_por_cnpj(session, doc) if tipo == "cnpj" else _buscar_por_cpf(session, doc)