from datetime import datetime

from backend.utils.sap_waits import wait_for_element, wait_until_ready


_CAMPO_FB03_DOCUMENTO = "wnd[0]/usr/txtRF05L-BELNR"
_CAMPO_FB03_EMPRESA = "wnd[0]/usr/ctxtRF05L-BUKRS"
_CAMPO_FB03_ANO = "wnd[0]/usr/txtRF05L-GJAHR"
_GRID_FB03 = "wnd[0]/usr/cntlCTRL_CONTAINERBSEG/shellcont/shell"
_POPUP_FB03_BANCO = "wnd[1]/usr/ctxtBSEG-HBKID"
_POPUP_FB03_FORMA = "wnd[1]/usr/ctxtBSEG-ZLSCH"


# Resposta padrao para o pos-faturamento.
def resultado_padrao(ok, etapa, mensagem, dados=None, erro_tecnico=None):
    return {
        "ok": ok,
        "etapa": etapa,
        "mensagem": mensagem,
        "dados": dados,
        "erro_tecnico": erro_tecnico,
    }


# Envia progresso separando FB03 e VF02_RESALVAR.
def _notificar(progress_callback, etapa, status, mensagem=None, percentual=None):
    if not callable(progress_callback):
        return

    try:
        progress_callback(etapa, status, mensagem, percentual)
    except Exception:
        return


# Repete a ação quando o SAP demora a disponibilizar controles.
def _retry(func, tentativas=3):
    ultimo_erro = None

    for _ in range(tentativas):
        try:
            return func()
        except Exception as exc:
            ultimo_erro = exc

    raise ultimo_erro or Exception("Falha apos varias tentativas.")


# Tenta sair da tela atual sem derrubar o fluxo em caso de falha.
def _encerrar_tela(session, tentativas=3):
    for _ in range(tentativas):
        try:
            session.findById("wnd[0]").sendVKey(3)
            wait_until_ready(session)
        except Exception:
            break


# Abre FB03 e ajusta banco/forma de pagamento no documento contábil.
def _ajustar_fb03(session, faturamento, progress_callback=None):
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nFB03"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, _CAMPO_FB03_DOCUMENTO).text = str(faturamento or "").strip()
    session.findById(_CAMPO_FB03_EMPRESA).text = "EMBA"
    session.findById(_CAMPO_FB03_EMPRESA).caretPosition = 4
    session.findById(_CAMPO_FB03_ANO).text = datetime.now().strftime("%Y")
    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    _notificar(
        progress_callback,
        "FB03",
        "processando",
        "Documento contábil carregado no FB03...",
        28,
    )

    def ajustar_item():
        grid = wait_for_element(session, _GRID_FB03)
        grid.currentCellColumn = "KOBEZ"
        grid.doubleClickCurrentCell()
        wait_until_ready(session)

        session.findById("wnd[0]/tbar[1]/btn[25]").press()
        wait_until_ready(session)
        session.findById("wnd[0]/tbar[1]/btn[8]").press()
        wait_until_ready(session)

    _retry(ajustar_item)

    _notificar(
        progress_callback,
        "FB03",
        "processando",
        "Selecionando dados bancarios no FB03...",
        62,
    )

    def tratar_popup():
        wait_for_element(session, _POPUP_FB03_BANCO).text = "BB100"
        session.findById(_POPUP_FB03_FORMA).text = "A"
        session.findById("wnd[1]/tbar[0]/btn[0]").press()
        wait_until_ready(session)

    _retry(tratar_popup)

    _notificar(
        progress_callback,
        "FB03",
        "processando",
        "Salvando ajuste contábil...",
        86,
    )

    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    wait_until_ready(session)


# Abre VF02 após o ajuste contábil e salva novamente o faturamento.
def _resalvar_vf02(session, progress_callback=None):
    # Após o FB03:
    # - volta da transação atual para a tela inicial
    # - abre VF02 por comando
    # - dá Enter
    # - salva
    # - volta
    for _ in range(2):
        try:
            session.findById("wnd[0]/tbar[0]/btn[12]").press()
            wait_until_ready(session)
        except Exception:
            break

    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVF02"
    session.findById("wnd[0]").sendVKey(0)
    wait_for_element(session, "wnd[0]/usr", timeout=8)
    wait_until_ready(session)

    _notificar(
        progress_callback,
        "VF02_RESALVAR",
        "processando",
        "Abrindo VF02 para re-salvar o faturamento...",
        34,
    )

    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    _notificar(
        progress_callback,
        "VF02_RESALVAR",
        "processando",
        "Confirmando dados do faturamento...",
        68,
    )

    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    wait_until_ready(session)

    _notificar(
        progress_callback,
        "VF02_RESALVAR",
        "processando",
        "Retornando da VF02...",
        90,
    )

    session.findById("wnd[0]/tbar[0]/btn[12]").press()
    wait_until_ready(session)


# Executa o pos-faturamento, podendo iniciar em FB03 ou retomar no re-salvamento.
def pos_faturamento(
    session,
    faturamento,
    logger,
    progress_callback=None,
    start_from="FB03",
):
    etapa_atual = str(start_from or "FB03").strip().upper()
    faturamento = str(faturamento or "").strip()
    progresso_atual = 0

    try:
        if etapa_atual == "FB03":
            progresso_atual = 12
            _notificar(
                progress_callback,
                "FB03",
                "processando",
                "Abrindo FB03 para ajuste contábil...",
                progresso_atual,
            )
            logger.add(4, "Abrindo FB03 para ajuste contábil...")
            _ajustar_fb03(session, faturamento, progress_callback=progress_callback)
            logger.add(4, "Ajuste contábil concluído no FB03.", publico=True)
            _notificar(
                progress_callback,
                "FB03",
                "concluido",
                "Ajuste contábil salvo.",
                100,
            )
            etapa_atual = "VF02_RESALVAR"

        if etapa_atual == "VF02_RESALVAR":
            progresso_atual = 12
            _notificar(
                progress_callback,
                "VF02_RESALVAR",
                "processando",
                "Retornando a VF02 para re-salvar o faturamento...",
                progresso_atual,
            )
            logger.add(5, "Retornando a VF02 para re-salvar o faturamento...")
            _resalvar_vf02(session, progress_callback=progress_callback)
            logger.add(5, "Faturamento re-salvo com sucesso.", publico=True)
            _notificar(
                progress_callback,
                "VF02_RESALVAR",
                "concluido",
                "Faturamento re-salvo com sucesso.",
                100,
            )

        return resultado_padrao(
            ok=True,
            etapa="VF02_RESALVAR",
            mensagem="Pós-faturamento concluído com sucesso.",
            dados={
                "faturamento": faturamento,
            },
        )

    except Exception as e:
        logger.add(5, f"Erro no pos-faturamento: {e}", nivel="ERRO")
        _notificar(
            progress_callback,
            etapa_atual,
            "erro",
            "Falha no pos-faturamento.",
            progresso_atual,
        )

        try:
            _encerrar_tela(session)
        except Exception:
            pass

        return resultado_padrao(
            ok=False,
            etapa=etapa_atual,
            mensagem="Erro ao executar o pos-faturamento.",
            dados={
                "faturamento": faturamento,
            },
            erro_tecnico=str(e),
        )
