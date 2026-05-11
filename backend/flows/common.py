import time


STATUS_BAR_ID = "wnd[0]/sbar"


# Resposta padrao compartilhada pelos fluxos SAP.
def resultado_padrao(ok, etapa, mensagem, dados=None, erro_tecnico=None):
    return {
        "ok": ok,
        "etapa": etapa,
        "mensagem": mensagem,
        "dados": dados,
        "erro_tecnico": erro_tecnico,
    }


# Envia progresso para a interface quando existe callback disponivel.
def notificar_progresso(
    progress_callback,
    etapa,
    status,
    mensagem=None,
    percentual=None,
):
    if not callable(progress_callback):
        return

    try:
        progress_callback(etapa, status, mensagem, percentual)
    except Exception:
        return


# Le propriedades COM do SAP tentando variacoes de maiuscula/minuscula.
def ler_propriedade(componente, *nomes):
    for nome in nomes:
        try:
            valor = getattr(componente, nome)
        except Exception:
            continue

        if valor is not None:
            return str(valor)

    return ""


# Le texto e tipo da barra de status do SAP.
def ler_status(session, status_bar_id=STATUS_BAR_ID):
    try:
        barra = session.findById(status_bar_id)
    except Exception:
        return "", ""

    texto = ler_propriedade(barra, "Text", "text").strip()
    tipo = ler_propriedade(barra, "MessageType", "messageType").strip().upper()
    return texto, tipo


# Atalho para quando a etapa precisa apenas do texto da barra de status.
def ler_status_texto(session, status_bar_id=STATUS_BAR_ID):
    return ler_status(session, status_bar_id=status_bar_id)[0]


# Aguarda a barra de status mudar depois de uma ação no SAP.
def aguardar_status_mudar(
    session,
    status_anterior="",
    timeout=10,
    interval=0.1,
    status_bar_id=STATUS_BAR_ID,
):
    deadline = time.monotonic() + max(0.0, float(timeout or 0.0))
    espera = max(0.05, float(interval or 0.2))
    ultimo_texto = status_anterior
    ultimo_tipo = ""

    while time.monotonic() < deadline:
        texto_atual, tipo_atual = ler_status(session, status_bar_id=status_bar_id)

        if texto_atual and texto_atual != status_anterior:
            return texto_atual, tipo_atual

        if texto_atual:
            ultimo_texto = texto_atual
            ultimo_tipo = tipo_atual

        time.sleep(espera)

    return ultimo_texto, ultimo_tipo
