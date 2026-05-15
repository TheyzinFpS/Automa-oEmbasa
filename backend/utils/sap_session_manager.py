import time

from backend.utils.sap_sessions import (
    contar_sessoes,
    descrever_sessao,
    dump_sessoes,
    iterar_sessoes_sap,
    localizar_sessao_spool,
    obter_aplicacao_da_sessao,
    sessao_ativa,
)


def obter_application(session):
    # Compatibilidade com fluxos antigos que chamavam sap_session_manager.
    return obter_aplicacao_da_sessao(session)


def iterar_sessoes(application):
    return [
        session
        for session in iterar_sessoes_sap(application)
        if sessao_ativa(session)
    ]


def adquirir_sessao_spool(application, timeout=10, interval=0.25):
    deadline = time.monotonic() + max(0.1, float(timeout or 0.1))

    while time.monotonic() < deadline:
        session = localizar_sessao_spool(application)

        if session is not None:
            return session

        time.sleep(interval)

    return None


def fingerprint(session):
    return descrever_sessao(session)
