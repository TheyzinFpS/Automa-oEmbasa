from datetime import datetime

from backend.flows.common import notificar_progresso, resultado_padrao
from backend.utils.sap_waits import wait_for_element
from backend.utils.timing import paced_sleep


_CAMPO_VF02_DOCUMENTO = "wnd[0]/usr/ctxtVBRK-VBELN"
_CAMPO_FB03_DOCUMENTO = "wnd[0]/usr/txtRF05L-BELNR"
_CAMPO_FB03_EMPRESA = "wnd[0]/usr/ctxtRF05L-BUKRS"
_CAMPO_FB03_ANO = "wnd[0]/usr/txtRF05L-GJAHR"
_GRID_FB03 = "wnd[0]/usr/cntlCTRL_CONTAINERBSEG/shellcont/shell"
_POPUP_FB03_BANCO = "wnd[1]/usr/ctxtBSEG-HBKID"
_POPUP_FB03_FORMA = "wnd[1]/usr/ctxtBSEG-ZLSCH"
_BOTAO_VF02_ITENS = "wnd[0]/tbar[1]/btn[5]"
_GRID_VF02_ITENS = "wnd[0]/usr/tblSAPMV60ATCTRL_UEB_FAKT"
_CAMPO_VF02_POSICAO = (
    "wnd[0]/usr/tblSAPMV60ATCTRL_UEB_FAKT/ctxtVBRP-POSNR[0,0]"
)
def _retry(func, tentativas=3, pausa=0.5):
    ultimo_erro = None

    for _ in range(max(1, int(tentativas))):
        try:
            return func()
        except Exception as exc:
            ultimo_erro = exc
            paced_sleep(pausa)

    if ultimo_erro is not None:
        raise ultimo_erro


def _retornar_para_tela_inicial(session, tentativas=3):
    for _ in range(max(1, int(tentativas))):
        try:
            session.findById("wnd[0]/tbar[0]/btn[15]").press()
            paced_sleep(0.2)
            continue
        except Exception:
            pass

        try:
            session.findById("wnd[0]/tbar[0]/btn[12]").press()
            paced_sleep(0.2)
            continue
        except Exception:
            break


def _abrir_vf02(session, documento):
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVF02"
    session.findById("wnd[0]").sendVKey(0)

    campo = wait_for_element(session, _CAMPO_VF02_DOCUMENTO)
    campo.text = documento
    session.findById("wnd[0]").sendVKey(0)
    paced_sleep(0.5)

    return campo.text.strip()


def _capturar_doc_fat_por_vf02(session, faturamento):
    doc_fat = _abrir_vf02(session, faturamento)
    if not doc_fat:
        raise Exception("Nao foi possivel confirmar o documento de faturamento na VF02.")

    _retornar_para_tela_inicial(session, tentativas=1)
    return doc_fat


def _ajustar_item_fb03(session):
    grid = wait_for_element(session, _GRID_FB03)
    grid.currentCellColumn = "KOBEZ"
    grid.doubleClickCurrentCell()

    session.findById("wnd[0]/tbar[1]/btn[25]").press()
    session.findById("wnd[0]/tbar[1]/btn[8]").press()


def _tratar_popup_fb03(session):
    wait_for_element(session, _POPUP_FB03_BANCO).text = "BB100"
    session.findById(_POPUP_FB03_FORMA).text = "A"
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    paced_sleep(0.4)


def _ajustar_fb03(session, doc_fat):
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nFB03"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, _CAMPO_FB03_DOCUMENTO).text = doc_fat
    session.findById(_CAMPO_FB03_EMPRESA).text = "EMBA"
    session.findById(_CAMPO_FB03_ANO).text = datetime.now().strftime("%Y")
    session.findById("wnd[0]").sendVKey(0)
    paced_sleep(0.5)

    _retry(lambda: _ajustar_item_fb03(session), tentativas=3, pausa=0.5)
    _retry(lambda: _tratar_popup_fb03(session), tentativas=3, pausa=0.5)

    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    paced_sleep(0.5)
    _retornar_para_tela_inicial(session, tentativas=1)


def _resalvar_vf02(session, doc_fat):
    _abrir_vf02(session, doc_fat)

    wait_for_element(session, _BOTAO_VF02_ITENS).press()
    paced_sleep(0.5)

    grid = wait_for_element(session, _GRID_VF02_ITENS)
    grid.getAbsoluteRow(0).selected = True

    campo_posicao = wait_for_element(session, _CAMPO_VF02_POSICAO)
    campo_posicao.setFocus()
    campo_posicao.caretPosition = 0

    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    paced_sleep(0.5)
    _retornar_para_tela_inicial(session, tentativas=2)


def pos_faturamento(
    session,
    faturamento,
    logger,
    progress_callback=None,
    start_from="VF02_CAPTURA",
    existing_doc_fat=None,
):
    etapa = start_from
    doc_fat = str(existing_doc_fat or "").strip() or None

    try:
        if etapa == "VF02_CAPTURA":
            notificar_progresso(
                progress_callback,
                "VF02_CAPTURA",
                "processando",
                "Confirmando documento de faturamento...",
                18,
            )

            if not doc_fat:
                doc_fat = _capturar_doc_fat_por_vf02(session, faturamento)
                logger.add(3, f"Doc. faturamento confirmado: {doc_fat}", publico=True)
            else:
                logger.add(3, f"Doc. faturamento reaproveitado da VF01: {doc_fat}")

            notificar_progresso(
                progress_callback,
                "VF02_CAPTURA",
                "concluido",
                f"Documento confirmado: {doc_fat}",
                100,
            )
            etapa = "FB03"

        if etapa == "FB03" and not doc_fat:
            raise Exception("Documento de faturamento ausente para iniciar o FB03.")

        if etapa == "FB03":
            notificar_progresso(
                progress_callback,
                "FB03",
                "processando",
                "Executando ajuste contabil...",
                20,
            )
            _ajustar_fb03(session, doc_fat)
            logger.add(4, "Ajuste contabil concluido no FB03.", publico=True)
            notificar_progresso(
                progress_callback,
                "FB03",
                "concluido",
                "Ajuste contabil concluido.",
                100,
            )
            etapa = "VF02_RESALVAR"

        if etapa == "VF02_RESALVAR":
            notificar_progresso(
                progress_callback,
                "VF02_RESALVAR",
                "processando",
                "Reabrindo VF02 para re-salvar o faturamento...",
                18,
            )
            _resalvar_vf02(session, doc_fat)
            logger.add(5, "Faturamento re-salvo com sucesso.", publico=True)
            notificar_progresso(
                progress_callback,
                "VF02_RESALVAR",
                "concluido",
                "VF02 re-salva com sucesso.",
                100,
            )

        return resultado_padrao(
            ok=True,
            etapa="VF02_RESALVAR",
            mensagem="Pos-faturamento concluido com sucesso.",
            dados={
                "faturamento": faturamento,
                "doc_fat": doc_fat,
            },
        )

    except Exception as exc:
        logger.add(5, f"Erro no pos-faturamento: {exc}", nivel="ERRO")
        notificar_progresso(
            progress_callback,
            etapa,
            "erro",
            f"Falha na etapa {etapa}.",
        )

        try:
            _retornar_para_tela_inicial(session, tentativas=3)
        except Exception:
            pass

        return resultado_padrao(
            ok=False,
            etapa=etapa,
            mensagem="Erro ao executar o pos-faturamento.",
            erro_tecnico=str(exc),
            dados={
                "faturamento": faturamento,
                "doc_fat": doc_fat,
            },
        )
