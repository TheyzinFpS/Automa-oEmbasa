from backend.cache.cliente_cache import ClienteCache
from backend.utils.sap_waits import (
    element_exists,
    press_and_wait,
    send_vkey_and_wait,
    wait_for_element,
)

cache_cliente = ClienteCache()

_CAMPO_CNPJ = (
    "wnd[2]/usr/tabsG_SELONETABSTRIP/tabpTAB006/"
    "ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/"
    "txtG_SELFLD_TAB-LOW[0,24]"
)
_CAMPO_CPF = (
    "wnd[2]/usr/tabsG_SELONETABSTRIP/tabpTAB006/"
    "ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/"
    "txtG_SELFLD_TAB-LOW[1,24]"
)
_CAMPO_CLIENTE = "wnd[1]/usr/ctxtRF02D-KUNNR"


def limpar_doc(doc):
    return "".join(filter(str.isdigit, str(doc)))


def tipo_documento(doc):
    if len(doc) == 11:
        return "cpf"
    if len(doc) == 14:
        return "cnpj"
    raise ValueError("Documento invalido")


def resultado_padrao(ok, etapa, mensagem, dados=None, erro_tecnico=None):
    return {
        "ok": ok,
        "etapa": etapa,
        "mensagem": mensagem,
        "dados": dados,
        "erro_tecnico": erro_tecnico,
    }


def _notificar(progress_callback, status, mensagem=None, percentual=None):
    if not callable(progress_callback):
        return

    try:
        progress_callback("XD03", status, mensagem, percentual)
    except Exception:
        return


def _abrir_xd03(session, logger):
    logger.add(0, "Abrindo XD03...")
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nXD03"
    send_vkey_and_wait(session, "wnd[0]", 0, "wnd[1]")


def _abrir_f4(session, logger):
    logger.add(0, "Abrindo ajuda de pesquisa...")
    send_vkey_and_wait(session, "wnd[1]", 4, "wnd[2]")


def _buscar(session, campo, doc, logger, tipo, progress_callback=None):
    campo_input = wait_for_element(session, campo)
    campo_input.text = doc

    logger.add(0, f"Pesquisando {tipo.upper()}: {doc}")
    _notificar(
        progress_callback,
        "processando",
        f"Consultando {tipo.upper()} no SAP...",
        58,
    )

    press_and_wait(session, "wnd[2]/tbar[0]/btn[0]")

    if element_exists(session, campo):
        logger.add(0, f"{tipo.upper()} nao encontrado")
        _notificar(
            progress_callback,
            "erro",
            f"{tipo.upper()} nao encontrado no SAP.",
            58,
        )

        press_and_wait(session, "wnd[2]/tbar[0]/btn[12]")
        press_and_wait(session, "wnd[1]/tbar[0]/btn[12]")

        return resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Cliente nao encontrado",
        )

    _notificar(progress_callback, "processando", "Confirmando resultado da busca...", 84)
    press_and_wait(session, "wnd[2]/tbar[0]/btn[0]")

    campo_cliente = wait_for_element(session, _CAMPO_CLIENTE)
    codigo = campo_cliente.text.strip()

    if not codigo:
        _notificar(
            progress_callback,
            "erro",
            "Codigo do cliente vazio na XD03.",
            84,
        )
        return resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Codigo do cliente vazio",
        )

    logger.add(0, f"Cliente encontrado: {codigo}")
    press_and_wait(session, "wnd[1]/tbar[0]/btn[12]")

    return resultado_padrao(
        ok=True,
        etapa="XD03",
        mensagem="Cliente encontrado",
        dados={
            "cliente": codigo,
            "documento": doc,
            "tipo_documento": tipo,
        },
    )


def buscar_cliente(session, dados, logger, progress_callback=None):
    try:
        doc = limpar_doc(dados["doc"])
        tipo = tipo_documento(doc)

        _notificar(
            progress_callback,
            "processando",
            "Preparando busca do cliente...",
            8,
        )

        cliente_cache = cache_cliente.get(doc)

        if cliente_cache:
            logger.add(
                0,
                f"Cliente encontrado no cache: {cliente_cache['cliente']}",
                publico=True,
            )
            _notificar(
                progress_callback,
                "concluido",
                "Cliente recuperado do cache.",
                100,
            )

            return resultado_padrao(
                ok=True,
                etapa="XD03",
                mensagem="Cliente recuperado do cache",
                dados=cliente_cache,
            )

        logger.add(0, "Cliente nao encontrado no cache. Consultando SAP...")
        _notificar(progress_callback, "processando", "Abrindo transacao XD03...", 18)
        _abrir_xd03(session, logger)

        _notificar(
            progress_callback,
            "processando",
            "Abrindo pesquisa de cliente...",
            34,
        )
        _abrir_f4(session, logger)

        if tipo == "cnpj":
            resultado = _buscar(
                session,
                _CAMPO_CNPJ,
                doc,
                logger,
                "cnpj",
                progress_callback=progress_callback,
            )
        else:
            resultado = _buscar(
                session,
                _CAMPO_CPF,
                doc,
                logger,
                "cpf",
                progress_callback=progress_callback,
            )

        if resultado["ok"]:
            cache_cliente.set(doc, resultado["dados"])
            logger.add(0, "Cliente salvo no cache")
            _notificar(
                progress_callback,
                "concluido",
                "Cliente localizado e confirmado.",
                100,
            )

        return resultado

    except Exception as e:
        logger.add(0, f"Erro XD03: {e}")
        _notificar(
            progress_callback,
            "erro",
            "Falha ao buscar cliente no XD03.",
        )

        return resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Erro ao buscar cliente",
            erro_tecnico=str(e),
        )
