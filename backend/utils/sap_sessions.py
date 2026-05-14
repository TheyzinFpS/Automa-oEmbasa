import time

from backend.utils.sap_waits import wait_until_ready


# IDs da tela inicial da F110 usados para confirmar que voltamos ao BOL correto.
F110_CAMPO_DATA_EXEC = "wnd[0]/usr/ctxtF110V-LAUFD"
F110_CAMPO_IDENT = "wnd[0]/usr/ctxtF110V-LAUFI"


def _safe_getattr(objeto, *nomes, default=""):
    for nome in nomes:
        try:
            valor = getattr(objeto, nome)
        except Exception:
            continue

        if valor is not None:
            return valor

    return default


def _safe_texto(valor):
    try:
        return str(valor or "").strip()
    except Exception:
        return ""


# Retorna a aplicação SAP GUI a partir de uma sessão já conhecida.
def obter_aplicacao_da_sessao(session):
    try:
        return session.Parent.Parent
    except Exception as exc:
        raise RuntimeError(f"Não foi possível obter a aplicação SAP GUI: {exc}") from exc


# Percorre todas as sessões abertas no mesmo SAP GUI.
def iterar_sessoes_sap(application):
    try:
        total_conexoes = int(application.Children.Count)
    except Exception:
        total_conexoes = 0

    for indice_conexao in range(total_conexoes):
        try:
            connection = application.Children(indice_conexao)
            total_sessoes = int(connection.Children.Count)
        except Exception:
            continue

        for indice_sessao in range(total_sessoes):
            try:
                yield connection.Children(indice_sessao)
            except Exception:
                continue


# Identidade estável da sessão. Normalmente vem como /app/con[0]/ses[1].
def identidade_sessao(session):
    identidade = _safe_texto(_safe_getattr(session, "Id", "id"))

    if identidade:
        return identidade

    return _safe_texto(session)


def sessao_ativa(session):
    try:
        session.findById("wnd[0]")
        return True
    except Exception:
        return False


def obter_transacao(session):
    try:
        info = session.Info
    except Exception:
        return ""

    return _safe_texto(
        _safe_getattr(info, "Transaction", "transaction", "TransactionCode")
    ).upper()


def obter_titulo_janela(session):
    try:
        janela = session.findById("wnd[0]")
    except Exception:
        return ""

    return _safe_texto(_safe_getattr(janela, "Text", "text")).upper()


def descrever_sessao(session):
    return {
        "id": identidade_sessao(session),
        "transaction": obter_transacao(session),
        "title": obter_titulo_janela(session),
        "active": sessao_ativa(session),
    }


def snapshot_sessoes(application):
    return {
        identidade_sessao(session): descrever_sessao(session)
        for session in iterar_sessoes_sap(application)
        if sessao_ativa(session)
    }


def mesma_sessao(sessao_a, sessao_b):
    if sessao_a is None or sessao_b is None:
        return False

    return identidade_sessao(sessao_a) == identidade_sessao(sessao_b)


def focar_sessao(session):
    janela = session.findById("wnd[0]")

    try:
        janela.maximize()
    except Exception:
        pass

    for metodo in ("setFocus", "SetFocus"):
        try:
            getattr(janela, metodo)()
            break
        except Exception:
            continue

    wait_until_ready(session)
    return session


def sessao_e_f110(session, data_exec=None, identificacao=None):
    transacao = obter_transacao(session)

    if transacao and transacao != "F110":
        return False

    try:
        campo_data = session.findById(F110_CAMPO_DATA_EXEC)
        campo_ident = session.findById(F110_CAMPO_IDENT)
    except Exception:
        return transacao == "F110"

    if data_exec and _safe_texto(
        _safe_getattr(campo_data, "Text", "text")
    ) != str(data_exec):
        return False

    if identificacao and _safe_texto(
        _safe_getattr(campo_ident, "Text", "text")
    ) != str(identificacao):
        return False

    return True


def sessao_e_spool(session):
    transacao = obter_transacao(session)
    titulo = obter_titulo_janela(session)

    if transacao in {"SP01", "SP02"}:
        return True

    marcadores_titulo = (
        "CONTROLE DE SAÍDA",
        "CONTROLE DE SAIDA",
        "SÍNTESE DAS ORDENS SPOOL",
        "SINTESE DAS ORDENS SPOOL",
        "SPOOL",
    )

    return any(marcador in titulo for marcador in marcadores_titulo)


def aguardar_nova_sessao(
    application,
    sessoes_antes,
    predicado=None,
    timeout=12,
    interval=0.2,
):
    antes = set(sessoes_antes or [])
    deadline = time.monotonic() + max(0.1, float(timeout or 0.1))
    candidatas = []

    while time.monotonic() < deadline:
        candidatas = [
            session
            for session in iterar_sessoes_sap(application)
            if identidade_sessao(session) not in antes and sessao_ativa(session)
        ]

        if predicado:
            for session in candidatas:
                try:
                    if predicado(session):
                        return session
                except Exception:
                    continue
        elif candidatas:
            return candidatas[0]

        time.sleep(interval)

    return candidatas[0] if candidatas else None


def localizar_sessao_f110(application, data_exec=None, identificacao=None):
    for session in iterar_sessoes_sap(application):
        try:
            if sessao_e_f110(session, data_exec=data_exec, identificacao=identificacao):
                return session
        except Exception:
            continue

    return None


def localizar_sessao_spool(application, ignorar_ids=None):
    ignorar_ids = set(ignorar_ids or [])

    for session in iterar_sessoes_sap(application):
        try:
            if identidade_sessao(session) in ignorar_ids:
                continue

            if sessao_e_spool(session):
                return session
        except Exception:
            continue

    return None


def localizar_sessao_por_transacao(application, transacao, ignorar_ids=None):
    transacao = _safe_texto(transacao).upper()
    ignorar_ids = set(ignorar_ids or [])

    if not transacao:
        return None

    for session in iterar_sessoes_sap(application):
        try:
            if identidade_sessao(session) in ignorar_ids:
                continue

            if obter_transacao(session) == transacao:
                return session
        except Exception:
            continue

    return None


def abrir_transacao_na_sessao(session, transacao):
    transacao = _safe_texto(transacao).upper()

    if not transacao:
        raise RuntimeError("Transação SAP não informada.")

    focar_sessao(session)
    campo_ok = session.findById("wnd[0]/tbar[0]/okcd")
    campo_ok.text = f"/n{transacao}"
    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)
    return session


def garantir_sessao_transacao(
    session,
    transacao,
    preferir_existente=True,
    abrir_se_necessario=True,
):
    transacao = _safe_texto(transacao).upper()

    if not transacao:
        return focar_sessao(session)

    if obter_transacao(session) == transacao:
        return focar_sessao(session)

    application = obter_aplicacao_da_sessao(session)

    if preferir_existente:
        encontrada = localizar_sessao_por_transacao(application, transacao)

        if encontrada:
            return focar_sessao(encontrada)

    if abrir_se_necessario:
        return abrir_transacao_na_sessao(session, transacao)

    return focar_sessao(session)


def fechar_sessao_principal(session, timeout=8):
    session_id = identidade_sessao(session)
    application = obter_aplicacao_da_sessao(session)

    try:
        janela = session.findById("wnd[0]")
    except Exception:
        return True

    for metodo in ("close", "Close"):
        try:
            getattr(janela, metodo)()
            break
        except Exception:
            continue

    _confirmar_fechamento_sessao(session)

    deadline = time.monotonic() + max(0.1, float(timeout or 0.1))

    while time.monotonic() < deadline:
        sessoes_atuais = snapshot_sessoes(application)

        if session_id not in sessoes_atuais:
            return True

        time.sleep(0.2)

    return session_id not in snapshot_sessoes(application)


def _confirmar_fechamento_sessao(session):
    for _ in range(3):
        try:
            popup = session.findById("wnd[1]")
        except Exception:
            return

        for element_id in (
            "usr/btnSPOP-OPTION1",
            "tbar[0]/btn[0]",
            "usr/btnBUTTON_1",
        ):
            try:
                popup.findById(element_id).press()
                wait_until_ready(session)
                break
            except Exception:
                continue
        else:
            try:
                popup.sendVKey(0)
                wait_until_ready(session)
            except Exception:
                return
