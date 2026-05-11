import time


# Espera um elemento SAP aparecer antes de interagir com ele.
def wait_for_element(session, element_id, timeout=8, interval=0.1):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            return session.findById(element_id)
        except Exception:
            time.sleep(interval)

    raise Exception(f"Elemento não encontrado: {element_id}")


# Aguarda o SAP liberar a sessão depois de um comando, sem delay fixo.
def wait_until_ready(session, timeout=8, interval=0.05):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            if not bool(session.Busy):
                return True
        except Exception:
            return True

        time.sleep(interval)

    return False


# Espera um elemento/janela desaparecer, util para popups.
def wait_until_not_exists(session, element_id, timeout=8):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            session.findById(element_id)
            time.sleep(0.1)
        except Exception:
            return True

    return False


# Verifica existencia sem disparar erro para o fluxo.
def element_exists(session, element_id):
    try:
        session.findById(element_id)
        return True
    except Exception:
        return False


# Atalho para aguardar uma janela específica do SAP.
def wait_for_window(session, window_id="wnd[1]", timeout=5):
    return wait_for_element(session, window_id, timeout)


# Pressiona um botão e opcionalmente aguarda outro elemento aparecer.
def press_and_wait(session, element_id, wait_id=None, timeout=5):
    session.findById(element_id).press()
    wait_until_ready(session, timeout=timeout)

    if wait_id:
        return wait_for_element(session, wait_id, timeout)

    return True


# Envia uma tecla SAP e opcionalmente aguarda um elemento de confirmação.
def send_vkey_and_wait(session, window_id, key, wait_id=None, timeout=5):
    session.findById(window_id).sendVKey(key)
    wait_until_ready(session, timeout=timeout)

    if wait_id:
        return wait_for_element(session, wait_id, timeout)

    return True


# Fecha janelas secundarias da sessao SAP atual, mantendo apenas wnd[0].
def fechar_janelas_secundarias(
    session,
    max_window_index=6,
    tentativas=3,
    timeout=3,
):
    fechadas = 0

    for _ in range(max(1, int(tentativas or 1))):
        fechou_alguma = False

        for indice in range(int(max_window_index or 6), 0, -1):
            window_id = f"wnd[{indice}]"

            try:
                janela = session.findById(window_id)
            except Exception:
                continue

            if _fechar_janela_secundaria_sap(janela):
                fechadas += 1
                fechou_alguma = True
                wait_until_ready(session, timeout=timeout)

        if not fechou_alguma:
            break

    return fechadas


# Tenta fechar popup/modal SAP usando as acoes menos invasivas primeiro.
def _fechar_janela_secundaria_sap(janela):
    for element_id in (
        "tbar[0]/btn[12]",
        "usr/btnSPOP-OPTION2",
        "usr/btnSPOP-OPTION3",
        "tbar[0]/btn[0]",
    ):
        try:
            janela.findById(element_id).press()
            return True
        except Exception:
            pass

    try:
        janela.sendVKey(12)
        return True
    except Exception:
        pass

    try:
        janela.close()
        return True
    except Exception:
        pass

    try:
        janela.Close()
        return True
    except Exception:
        return False
