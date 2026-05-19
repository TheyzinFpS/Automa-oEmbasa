from datetime import datetime, timedelta

from backend.flows.f110_boleto import finalizar_boleto_f110
from backend.utils.sap_waits import wait_for_element, wait_until_ready


_CAMPO_DATA_EXEC = "wnd[0]/usr/ctxtF110V-LAUFD"
_CAMPO_IDENT = "wnd[0]/usr/ctxtF110V-LAUFI"

_ABA_PAR = "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR"
_CAMPO_PAR_EMPRESA = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/"
    "ssubSUBSCREEN_BODY:SAPF110V:0202/"
    "tblSAPF110VCTRL_FKTTAB/txtF110V-BUKLS[0,0]"
)
_CAMPO_PAR_FORMA = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/"
    "ssubSUBSCREEN_BODY:SAPF110V:0202/"
    "tblSAPF110VCTRL_FKTTAB/ctxtF110V-ZWELS[1,0]"
)
_CAMPO_PAR_DATA_LANC = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/"
    "ssubSUBSCREEN_BODY:SAPF110V:0202/"
    "tblSAPF110VCTRL_FKTTAB/ctxtF110V-NEDAT[2,0]"
)
_CAMPO_PAR_CLIENTE = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpPAR/"
    "ssubSUBSCREEN_BODY:SAPF110V:0202/"
    "subSUBSCR_SEL:SAPF110V:7004/ctxtR_KUNNR-LOW"
)

_ABA_SEL = "wnd[0]/usr/tabsF110_TABSTRIP/tabpSEL"
_CAMPO_SEL_TEXTO1 = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpSEL/"
    "ssubSUBSCREEN_BODY:SAPF110V:0203/"
    "sub:SAPF110V:0203/ctxtF110V-TEXT1[0,11]"
)
_CAMPO_SEL_LISTA1 = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpSEL/"
    "ssubSUBSCREEN_BODY:SAPF110V:0203/"
    "sub:SAPF110V:0203/txtF110V-LIST1[1,11]"
)

_ABA_LOG = "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG"
_CHK_LOG_1 = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/"
    "ssubSUBSCREEN_BODY:SAPF110V:0204/chkF110V-XTRFA"
)
_CHK_LOG_2 = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/"
    "ssubSUBSCREEN_BODY:SAPF110V:0204/chkF110V-XTRZE"
)
_CHK_LOG_3 = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/"
    "ssubSUBSCREEN_BODY:SAPF110V:0204/chkF110V-XTRBL"
)
_CAMPO_LOG_VONKD = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/"
    "ssubSUBSCREEN_BODY:SAPF110V:0204/sub:SAPF110V:0204/txtF110V-VONKD[0,23]"
)
_CAMPO_LOG_BISKD = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpLOG/"
    "ssubSUBSCREEN_BODY:SAPF110V:0204/sub:SAPF110V:0204/txtF110V-BISKD[0,34]"
)

_ABA_PRI = "wnd[0]/usr/tabsF110_TABSTRIP/tabpPRI"
_CAMPO_PRI_VARIANTE = (
    "wnd[0]/usr/tabsF110_TABSTRIP/tabpPRI/"
    "ssubSUBSCREEN_BODY:SAPF110V:0205/"
    "tblSAPF110VCTRL_DRPTAB/ctxtF110V-VARI1[1,2]"
)

_ABA_STA = "wnd[0]/usr/tabsF110_TABSTRIP/tabpSTA"


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


def safe_find(session, element_id):
    try:
        return session.findById(element_id)
    except Exception:
        return None

def _somente_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())




def abrir_f110(session):
    # Abre a F110 diretamente por OKCODE, sem depender da árvore do SAP.
    wait_for_element(session, "wnd[0]").maximize()

    campo_ok = wait_for_element(session, "wnd[0]/tbar[0]/okcd")
    campo_ok.text = "/nF110"

    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)
    wait_for_element(session, _CAMPO_DATA_EXEC, timeout=10)


def _ultimo_dia_do_mes(data):
    prox_mes = data.replace(day=28) + timedelta(days=4)
    return prox_mes - timedelta(days=prox_mes.day)


def ultimo_dia_mes():
    # Retorna a Próx.data.lan da F110 no formato ddmmyyyy.
    # Se hoje não for o último dia do mês, usa o último dia do mês atual.
    # Se hoje for o último dia do mês, usa o último dia do mês seguinte.
    hoje = datetime.now()
    ultimo_atual = _ultimo_dia_do_mes(hoje)

    if hoje.date() == ultimo_atual.date():
        primeiro_dia_mes_seguinte = ultimo_atual + timedelta(days=1)
        ultimo_seguinte = _ultimo_dia_do_mes(primeiro_dia_mes_seguinte)
        return ultimo_seguinte.strftime("%d%m%Y")

    return ultimo_atual.strftime("%d%m%Y")


def gerar_identificacao(session, data_exec):
    """
    Encontra a primeira identificação BOLxx livre para a data de execução.

    Ajuste importante:
    - Testa BOL01 até BOL100.
    - Não usa mais o botão de status btn[20] para decidir se a BOL está livre,
      porque isso estava fazendo o fluxo parar/travar em BOL10/BOL11.
    - A BOL é considerada ocupada quando, na aba Parâmetro, já existe cliente
      preenchido no campo de cliente.
    - Ao encontrar uma BOL livre, volta para Status e retorna a identificação.
    """

    for i in range(1, 101):
        ident = f"BOL{i:02d}"

        wait_for_element(session, _CAMPO_DATA_EXEC, timeout=10).text = data_exec
        wait_for_element(session, _CAMPO_IDENT, timeout=10).text = ident
        session.findById("wnd[0]").sendVKey(0)
        wait_until_ready(session)

        try:
            wait_for_element(session, _ABA_PAR, timeout=10).select()
            wait_until_ready(session)

            campo_cliente = wait_for_element(
                session,
                _CAMPO_PAR_CLIENTE,
                timeout=8,
            )

            if campo_cliente.text.strip():
                wait_for_element(session, _ABA_STA, timeout=10).select()
                wait_until_ready(session)
                continue

            wait_for_element(session, _ABA_STA, timeout=10).select()
            wait_until_ready(session)
            return ident

        except Exception:
            # Se a aba Parâmetro/campo cliente não existir ainda para a BOL,
            # tratamos como livre, mas deixamos a tela estabilizada em Status.
            try:
                wait_for_element(session, _ABA_STA, timeout=5).select()
                wait_until_ready(session)
            except Exception:
                pass

            return ident

    raise Exception("Nenhuma identificação disponível entre BOL01 e BOL100 para o F110.")



def preencher_parametros(session, cliente, data_lanc):
    """
    Preenche empresa, método de pagamento, próxima data de lançamento e cliente.

    Correção:
    - O SAP recebe 31052026, mas exibe 31.05.2026.
    - Por isso a validação da data compara apenas os dígitos.
    """

    wait_for_element(session, _ABA_PAR, timeout=10).select()
    wait_until_ready(session)

    campo_empresa = wait_for_element(session, _CAMPO_PAR_EMPRESA, timeout=10)
    campo_forma = wait_for_element(session, _CAMPO_PAR_FORMA, timeout=10)
    campo_data_lanc = wait_for_element(session, _CAMPO_PAR_DATA_LANC, timeout=10)
    campo_cliente = wait_for_element(session, _CAMPO_PAR_CLIENTE, timeout=10)

    campo_empresa.setFocus()
    campo_empresa.text = "EMBA"

    campo_forma.setFocus()
    campo_forma.text = "A"

    campo_data_lanc.setFocus()
    campo_data_lanc.text = data_lanc

    cliente_txt = str(cliente).strip()
    campo_cliente.setFocus()
    campo_cliente.text = cliente_txt
    campo_cliente.caretPosition = len(cliente_txt)

    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    campo_empresa = wait_for_element(session, _CAMPO_PAR_EMPRESA, timeout=10)
    campo_forma = wait_for_element(session, _CAMPO_PAR_FORMA, timeout=10)
    campo_data_lanc = wait_for_element(session, _CAMPO_PAR_DATA_LANC, timeout=10)
    campo_cliente = wait_for_element(session, _CAMPO_PAR_CLIENTE, timeout=10)

    if campo_empresa.text.strip().upper() != "EMBA":
        raise Exception("Empresa EMBA não foi preenchida nos parâmetros da F110.")

    if campo_forma.text.strip().upper() != "A":
        raise Exception("Forma de pagamento A não foi preenchida nos parâmetros da F110.")

    if _somente_digitos(campo_data_lanc.text) != _somente_digitos(data_lanc):
        raise Exception(
            "Próxima data de lançamento não foi preenchida nos parâmetros da F110. "
            f"SAP={campo_data_lanc.text} esperado={data_lanc}"
        )

    if campo_cliente.text.strip() != cliente_txt:
        raise Exception("Cliente não foi preenchido nos parâmetros da F110.")



def preencher_selecao_livre(session, doc_formatado):
    """
    Preenche a seleção livre com 00 + doc_fat.
    Força a troca para a aba Seleção livre após os parâmetros.
    """

    for _ in range(2):
        wait_for_element(session, _ABA_SEL, timeout=10).select()
        wait_until_ready(session)

    campo_texto1 = wait_for_element(session, _CAMPO_SEL_TEXTO1, timeout=10)
    campo_texto1.setFocus()
    campo_texto1.caretPosition = 0

    session.findById("wnd[0]").sendVKey(4)
    wait_for_element(session, "wnd[1]", timeout=8)

    try:
        session.findById("wnd[1]").sendVKey(2)
        wait_until_ready(session)
    except Exception:
        try:
            session.findById("wnd[1]/tbar[0]/btn[0]").press()
            wait_until_ready(session)
        except Exception:
            pass

    campo_lista = wait_for_element(session, _CAMPO_SEL_LISTA1, timeout=10)
    campo_lista.text = doc_formatado
    campo_lista.setFocus()
    campo_lista.caretPosition = len(doc_formatado)

    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    campo_lista = wait_for_element(session, _CAMPO_SEL_LISTA1, timeout=10)
    if campo_lista.text.strip() != doc_formatado:
        raise Exception("Erro ao preencher a seleção livre do F110.")



def configurar_log(session, cliente):
    # Marca opções de log e informa o intervalo do cliente.
    wait_for_element(session, _ABA_LOG).select()
    wait_until_ready(session)

    chk1 = session.findById(_CHK_LOG_1)
    chk2 = session.findById(_CHK_LOG_2)
    chk3 = session.findById(_CHK_LOG_3)

    chk1.selected = True
    chk2.selected = True
    chk3.selected = True

    campo_vonkd = session.findById(_CAMPO_LOG_VONKD)
    campo_biskd = session.findById(_CAMPO_LOG_BISKD)

    campo_vonkd.text = str(cliente).strip()
    campo_biskd.text = str(cliente).strip()
    campo_biskd.setFocus()
    campo_biskd.caretPosition = len(str(cliente).strip())

    if not (chk1.selected and chk2.selected and chk3.selected):
        raise Exception("Erro ao marcar os checkboxes do LOG no F110.")

    if campo_vonkd.text.strip() != str(cliente).strip():
        raise Exception("Erro ao preencher VONKD no LOG do F110.")

    if campo_biskd.text.strip() != str(cliente).strip():
        raise Exception("Erro ao preencher BISKD no LOG do F110.")


def configurar_impressao(session):
    # Configura a variante de impressão do boleto.
    wait_for_element(session, _ABA_PRI).select()
    wait_until_ready(session)

    campo_variante = wait_for_element(session, _CAMPO_PRI_VARIANTE)
    campo_variante.text = "BB_BOLETO_REC"
    campo_variante.setFocus()
    campo_variante.caretPosition = len("BB_BOLETO_REC")


def tratar_popups_status(session):
    # Trata popups obrigatórios da aba Status antes da execução final.
    wait_for_element(session, _ABA_STA).select()
    wait_until_ready(session)

    for element_id in ("usr/btnSPOP-OPTION1", "tbar[0]/btn[0]"):
        try:
            popup = safe_find(session, "wnd[1]")
            if popup:
                popup.findById(element_id).press()
                wait_until_ready(session)
        except Exception:
            pass

    session.findById(_ABA_STA).select()
    wait_until_ready(session)

    try:
        popup = safe_find(session, "wnd[1]")
        if popup:
            popup.findById("usr/btnSPOP-OPTION1").press()
            wait_until_ready(session)
    except Exception:
        pass


def executar_proposta(session):
    # Executa a proposta de pagamento imediata.
    wait_for_element(session, "wnd[0]").maximize()
    session.findById("wnd[0]/tbar[1]/btn[13]").press()

    popup = wait_for_element(session, "wnd[1]")
    chk_imediata = popup.findById("usr/chkF110V-XSTRF")

    try:
        ja_marcado = bool(chk_imediata.selected)
    except Exception:
        ja_marcado = False

    if not ja_marcado:
        chk_imediata.selected = True
        chk_imediata.setFocus()

    popup.findById("tbar[0]/btn[0]").press()
    wait_until_ready(session)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)


def executar_pagamento_e_impressao(session, identificacao):
    # Executa pagamento/impressão e retorna o nome do job gerado.
    session.findById("wnd[0]/tbar[1]/btn[7]").press()

    popup_pag = wait_for_element(session, "wnd[1]")
    campo_check = popup_pag.findById("usr/chkF110V-XMITD")
    campo_check.selected = True
    campo_check.setFocus()
    popup_pag.findById("tbar[0]/btn[0]").press()
    wait_until_ready(session)

    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    session.findById("wnd[0]/tbar[1]/btn[6]").press()
    wait_until_ready(session)

    popup_job = wait_for_element(session, "wnd[1]")
    job_name = f"F110-{datetime.now().strftime('%Y%m%d')}-{identificacao}-1"
    campo_job = popup_job.findById("usr/txtTBTCO-JOBNAME")
    campo_job.text = job_name
    campo_job.setFocus()
    campo_job.caretPosition = len(job_name)
    popup_job.findById("tbar[0]/btn[0]").press()
    wait_until_ready(session)

    return job_name


def f110(session, cliente, doc_fat, logger, progress_callback=None, dados=None):
    # Fluxo completo da F110, incluindo finalização de boleto/remessa.
    data_exec = datetime.now().strftime("%d%m%Y")
    data_lanc = ultimo_dia_mes()
    doc_formatado = f"00{str(doc_fat).strip()}"
    identificacao = None
    job_name = None
    finalizacao_boleto = {}

    try:
        logger.add(6, "Abrindo F110...", publico=True)
        logger.add(6, f"Data de execução F110: {data_exec}")
        logger.add(6, f"Próxima data de lançamento F110: {data_lanc}")
        _notificar(progress_callback, "processando", "Abrindo F110...", 10)

        abrir_f110(session)

        _notificar(progress_callback, "processando", "Gerando identificação BOL...", 20)
        identificacao = gerar_identificacao(session, data_exec)
        logger.add(6, f"Identificação F110 selecionada: {identificacao}")

        _notificar(progress_callback, "processando", "Preenchendo parâmetros do F110...", 34)
        preencher_parametros(session, cliente, data_lanc)
        logger.add(6, "Parâmetros da F110 preenchidos e validados.", publico=True)

        _notificar(progress_callback, "processando", "Preenchendo seleção livre...", 48)
        preencher_selecao_livre(session, doc_formatado)
        logger.add(6, "Seleção livre da F110 preenchida e validada.", publico=True)

        _notificar(progress_callback, "processando", "Configurando log...", 60)
        configurar_log(session, cliente)

        _notificar(progress_callback, "processando", "Configurando impressão...", 70)
        configurar_impressao(session)

        _notificar(progress_callback, "processando", "Tratando status do F110...", 78)
        tratar_popups_status(session)

        _notificar(progress_callback, "processando", "Executando proposta...", 86)
        executar_proposta(session)

        _notificar(progress_callback, "processando", "Executando pagamento e impressão...", 96)
        job_name = executar_pagamento_e_impressao(session, identificacao)

        finalizacao_boleto = finalizar_boleto_f110(
            session,
            logger=logger,
            progress_callback=progress_callback,
            dados=dados,
            cliente=cliente,
            numero_boleto=doc_fat,
            data_exec=data_exec,
            identificacao=identificacao,
        )

        logger.add(6, f"F110 finalizado com sucesso. Job: {job_name}", publico=True)
        _notificar(progress_callback, "concluido", "F110 finalizado com sucesso.", 100)

        return resultado_padrao(
            ok=True,
            etapa="F110",
            mensagem="F110 finalizado com sucesso.",
            dados={
                "boleto": "GERADO",
                "identificacao_pagamento": identificacao,
                "job_name": job_name,
                "cliente": cliente,
                "doc_fat": doc_fat,
                "data_execucao": data_exec,
                "proxima_data_lancamento": data_lanc,
                **finalizacao_boleto,
            },
        )

    except Exception as e:
        logger.add(6, f"Erro F110: {e}", nivel="ERRO")
        _notificar(progress_callback, "erro", "Falha ao executar F110.", 96)

        return resultado_padrao(
            ok=False,
            etapa="F110",
            mensagem="Erro ao executar o F110.",
            dados={
                "cliente": cliente,
                "doc_fat": doc_fat,
                "identificacao_pagamento": identificacao,
                "job_name": job_name,
                **finalizacao_boleto,
            },
            erro_tecnico=str(e),
        )
