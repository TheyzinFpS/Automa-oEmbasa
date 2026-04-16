from datetime import datetime, timedelta


VARIANTE_IMPRESSAO = "BB_BOLETO_REC"
EMPRESA_F110 = "EMBA"
METODO_F110 = "A"


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
        progress_callback("F110", status, mensagem, percentual)
    except Exception:
        return


def _ultimo_dia_mes():
    hoje = datetime.now()
    proximo_mes = hoje.replace(day=28) + timedelta(days=4)
    ultimo = proximo_mes - timedelta(days=proximo_mes.day)
    return ultimo.strftime("%d%m%Y")


def _montar_contexto_mock(cliente, doc_fat):
    data_execucao = datetime.now().strftime("%d%m%Y")
    data_lancamento = _ultimo_dia_mes()
    identificacao = "BOL01"
    documento_selecao = f"00{doc_fat}"

    return {
        "cliente": str(cliente or "").strip(),
        "doc_fat": str(doc_fat or "").strip(),
        "data_execucao": data_execucao,
        "data_lancamento": data_lancamento,
        "identificacao_pagamento": identificacao,
        "documento_selecao": documento_selecao,
        "empresa": EMPRESA_F110,
        "metodo": METODO_F110,
        "variante_impressao": VARIANTE_IMPRESSAO,
    }


def f110(session, cliente, doc_fat, logger, progress_callback=None):
    del session

    try:
        contexto = _montar_contexto_mock(cliente, doc_fat)

        logger.add(
            6,
            "F110 executado em modo mockado para preparacao de testes.",
            publico=True,
        )
        logger.add(6, f"Cliente preparado para F110: {contexto['cliente']}")
        logger.add(6, f"Documento livre preparado: {contexto['documento_selecao']}")
        logger.add(6, f"Empresa F110: {contexto['empresa']}")
        logger.add(6, f"Metodo de pagamento: {contexto['metodo']}")
        logger.add(6, f"Variante de impressao: {contexto['variante_impressao']}")

        _notificar(progress_callback, "processando", "Abrindo contexto da F110...", 12)
        _notificar(
            progress_callback,
            "processando",
            "Montando parametros de pagamento em modo mockado...",
            36,
        )
        _notificar(
            progress_callback,
            "processando",
            "Preparando selecao livre e log em modo mockado...",
            68,
        )
        _notificar(
            progress_callback,
            "processando",
            "Finalizando simulacao da F110...",
            92,
        )
        _notificar(progress_callback, "concluido", "F110 mockado concluido.", 100)

        return resultado_padrao(
            ok=True,
            etapa="F110",
            mensagem="F110 mockado concluido com sucesso.",
            dados={
                "boleto": "Mockado",
                "identificacao_pagamento": contexto["identificacao_pagamento"],
                "doc_fat": contexto["doc_fat"],
                "cliente": contexto["cliente"],
                "data_execucao": contexto["data_execucao"],
                "data_lancamento": contexto["data_lancamento"],
                "documento_selecao": contexto["documento_selecao"],
            },
        )

    except Exception as exc:
        logger.add(6, f"Erro no F110 mockado: {exc}", nivel="ERRO")
        _notificar(progress_callback, "erro", "Falha ao executar o F110 mockado.")

        return resultado_padrao(
            ok=False,
            etapa="F110",
            mensagem="Erro ao executar o F110 mockado.",
            erro_tecnico=str(exc),
            dados={
                "cliente": str(cliente or "").strip(),
                "doc_fat": str(doc_fat or "").strip(),
            },
        )
