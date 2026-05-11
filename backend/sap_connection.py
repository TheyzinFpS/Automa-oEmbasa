SAP_STARTUP_MESSAGE = (
    "Não foi possível localizar uma sessão logada do SAP.\n\n"
    "Abra o SAP, faça login e tente novamente."
)


# Importa pywin32 somente quando o app precisa conversar com o SAP GUI.
def _importar_win32com():
    try:
        import win32com.client  # type: ignore

        return win32com.client
    except ImportError as exc:
        raise Exception(
            "Não foi possível importar o pywin32/win32com. "
            "Instale o pywin32 no ambiente Python usado pelo projeto."
        ) from exc


# Percorre todas as conexoes/sessoes abertas no SAP GUI.
def _iterar_sessoes(application):
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


# Considera a sessão pronta quando já existe janela principal e campo de comando.
def _sessao_esta_pronta(session):
    session.findById("wnd[0]")
    session.findById("wnd[0]/tbar[0]/okcd")
    return True


# Diagnostica se existe uma sessão SAP logada e pronta para automação.
def diagnosticar_sap():
    try:
        win32_client = _importar_win32com()
        sap_gui = win32_client.GetObject("SAPGUI")
        application = sap_gui.GetScriptingEngine
    except Exception as exc:
        return {
            "ok": False,
            "mensagem": SAP_STARTUP_MESSAGE,
            "erro_tecnico": str(exc),
            "session": None,
        }

    ultimo_erro = "Nenhuma sessão SAP pronta foi encontrada."

    for session in _iterar_sessoes(application):
        try:
            _sessao_esta_pronta(session)
            return {
                "ok": True,
                "mensagem": "",
                "erro_tecnico": "",
                "session": session,
            }
        except Exception as exc:
            ultimo_erro = str(exc)

    return {
        "ok": False,
        "mensagem": SAP_STARTUP_MESSAGE,
        "erro_tecnico": ultimo_erro,
        "session": None,
    }


# Retorna a sessão SAP pronta ou dispara erro explicativo para o controller.
def conectar_sap():
    diagnostico = diagnosticar_sap()

    if diagnostico["ok"]:
        return diagnostico["session"]

    raise Exception(
        f"{diagnostico['mensagem']} Detalhe tecnico: {diagnostico['erro_tecnico']}"
    )
