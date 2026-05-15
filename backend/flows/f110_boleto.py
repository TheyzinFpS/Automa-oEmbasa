import ctypes
import re

from backend.documentos import formatar_doc
from backend.utils.sap_sessions import (
    aguardar_nova_sessao,
    aguardar_quantidade_sessoes,
    contar_sessoes,
    dump_sessoes,
    fechar_sessao_principal,
    fingerprint_sessao,
    focar_sessao,
    identidade_sessao,
    iterar_sessoes_sap,
    localizar_sessao_f110,
    localizar_sessao_por_id,
    localizar_sessao_spool,
    mesma_sessao,
    obter_aplicacao_da_sessao,
    sessao_e_f110,
    sessao_e_spool,
    snapshot_sessoes,
)
from backend.utils.sap_waits import wait_for_element, wait_until_ready


_TIPOS_LABEL = {
    "viabilidade": "Viabilidade",
    "agua": "Projeto Água",
    "esgoto": "Projeto Esgoto",
}

_MB_YESNO = 0x00000004
_MB_ICONQUESTION = 0x00000020
_MB_TOPMOST = 0x00040000
_IDYES = 6


def _abrir_transacao(session, codigo, wait_id="wnd[0]/usr", timeout=10):
    # Abre transações via OKCODE, evitando dependência de menus/nodes do SAP.
    wait_for_element(session, "wnd[0]").maximize()

    campo_ok = wait_for_element(
        session,
        "wnd[0]/tbar[0]/okcd",
        timeout=5,
    )
    campo_ok.text = f"/n{codigo}"

    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    if wait_id:
        return wait_for_element(session, wait_id, timeout=timeout)

    return True


def _abrir_transacao_nova_sessao(session, codigo):
    # /o abre a transação em uma nova sessão SAP, preservando a F110 original.
    wait_for_element(session, "wnd[0]").maximize()

    campo_ok = wait_for_element(
        session,
        "wnd[0]/tbar[0]/okcd",
        timeout=5,
    )
    campo_ok.text = f"/o{codigo}"

    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)


def _notificar(progress_callback, mensagem, percentual, status="processando"):
    # Sincroniza a etapa F110 com o progresso em tempo real da interface.
    if not callable(progress_callback):
        return

    try:
        progress_callback("F110", status, mensagem, percentual)
    except Exception:
        return


def _limpar_parte_nome_arquivo(valor, fallback="INFORMAR"):
    texto = str(valor or "").strip() or fallback
    texto = re.sub(r'[<>:"/\\|?*]+', "-", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" .-") or fallback


def montar_nome_pdf_sugerido(numero_boleto, dados=None, cliente=None):
    # Monta o padrão de nome que o usuário deve colar no PDFCreator.
    dados = dados or {}
    endereco = dados.get("endereco") or {}
    tipo = str(dados.get("tipo") or "").strip().lower()

    nome_cliente = (
        dados.get("nome_cliente")
        or dados.get("cliente_nome")
        or dados.get("razao_social")
        or dados.get("nome")
    )

    documento = (dados.get("doc_info") or {}).get("formatado") or formatar_doc(
        dados.get("doc", "")
    )

    fallback_cliente = (
        f"CLIENTE {cliente}"
        if cliente
        else ("NOME DO CLIENTE OU EMPRESA" + (f" {documento}" if documento else ""))
    )

    partes = [
        _limpar_parte_nome_arquivo(numero_boleto, "NUMERO DO BOLETO"),
        _limpar_parte_nome_arquivo(nome_cliente, fallback_cliente),
        _limpar_parte_nome_arquivo(
            endereco.get("empreendimento"),
            "NOME DO EMPREENDIMENTO",
        ),
        _limpar_parte_nome_arquivo(_TIPOS_LABEL.get(tipo, tipo), "TIPO DO PEDIDO"),
    ]

    return " - ".join(partes)


def _mensagem_confirmacao_pdf(nome_pdf_sugerido):
    return (
        "Gere o boleto no PDFCreator antes de continuar.\n\n"
        "Use o seguinte padrão para o nome do PDF:\n\n"
        f"{nome_pdf_sugerido}\n\n"
        "Depois de criar/salvar o PDF, clique em SIM para prosseguir.\n\n"
        "Clique em NÃO se ainda não finalizou o PDF."
    )


def _confirmar_pdf_boleto_messagebox(nome_pdf_sugerido):
    mensagem = _mensagem_confirmacao_pdf(nome_pdf_sugerido)

    resposta = ctypes.windll.user32.MessageBoxW(
        None,
        mensagem,
        "EMBASA - Confirmação do boleto",
        _MB_YESNO | _MB_ICONQUESTION | _MB_TOPMOST,
    )

    if resposta != _IDYES:
        raise RuntimeError("Geração do PDF do boleto não confirmada pelo usuário.")


def confirmar_pdf_boleto(nome_pdf_sugerido):
    # Popup local com botão de copiar nome e confirmação manual do PDF.
    try:
        import tkinter as tk
    except Exception:
        _confirmar_pdf_boleto_messagebox(nome_pdf_sugerido)
        return

    confirmado = {"valor": False}
    root = tk.Tk()
    root.title("EMBASA - Confirmação do boleto")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    def copiar_nome():
        root.clipboard_clear()
        root.clipboard_append(nome_pdf_sugerido)
        root.update()
        status_var.set("Nome copiado. Cole no PDFCreator.")

    def confirmar():
        confirmado["valor"] = True
        root.destroy()

    def cancelar():
        confirmado["valor"] = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", cancelar)

    frame = tk.Frame(root, padx=18, pady=16)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text="Gere o boleto no PDFCreator antes de continuar.",
        font=("Segoe UI", 10, "bold"),
        anchor="w",
        justify="left",
    ).pack(fill="x")

    tk.Label(
        frame,
        text="Use o nome abaixo para salvar o PDF:",
        font=("Segoe UI", 9),
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=(10, 4))

    nome_var = tk.StringVar(value=nome_pdf_sugerido)
    nome_input = tk.Entry(
        frame,
        textvariable=nome_var,
        width=96,
        font=("Segoe UI", 9),
        state="readonly",
        readonlybackground="#ffffff",
    )
    nome_input.pack(fill="x")

    status_var = tk.StringVar(value="Clique em Copiar nome para usar no PDFCreator.")
    tk.Label(
        frame,
        textvariable=status_var,
        font=("Segoe UI", 8),
        fg="#345",
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=(8, 12))

    botoes = tk.Frame(frame)
    botoes.pack(fill="x")

    tk.Button(
        botoes,
        text="Copiar nome",
        width=16,
        command=copiar_nome,
    ).pack(side="left")

    tk.Button(
        botoes,
        text="PDF gerado, prosseguir",
        width=24,
        command=confirmar,
    ).pack(side="right")

    tk.Button(
        botoes,
        text="Cancelar",
        width=12,
        command=cancelar,
    ).pack(side="right", padx=(0, 8))

    root.update_idletasks()

    largura = root.winfo_width()
    altura = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (largura // 2)
    y = (root.winfo_screenheight() // 2) - (altura // 2)

    root.geometry(f"+{max(0, x)}+{max(0, y)}")
    root.lift()
    root.focus_force()
    root.mainloop()

    if not confirmado["valor"]:
        raise RuntimeError("Geração do PDF do boleto não confirmada pelo usuário.")


def fechar_popups_se_existirem(session, max_tentativas=5):
    # Fecha confirmações intermediárias antes de navegar entre spool/F110/remessa.
    for _ in range(max_tentativas):
        try:
            wnd1 = session.findById("wnd[1]")
        except Exception:
            break

        try:
            wnd1.sendVKey(0)
        except Exception:
            try:
                wnd1.close()
            except Exception:
                pass

        try:
            wait_until_ready(session)
        except Exception:
            pass


def abrir_ordens_spool_boleto(
    session,
    logger=None,
    progress_callback=None,
):
    _notificar(
        progress_callback,
        "Abrindo ordens spool próprias...",
        97,
    )

    _abrir_transacao(
        session,
        "SP02",
        wait_id="wnd[0]/usr",
        timeout=12,
    )

    if logger:
        logger.add(
            6,
            "Ordens spool próprias abertas.",
            publico=True,
        )

    _notificar(
        progress_callback,
        "Ordens spool abertas. Gere o PDF no PDFCreator.",
        98,
    )

    return {
        "spool_boleto": "ABERTO",
    }


def abrir_ordens_spool_boleto_em_nova_sessao(
    session,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    # Abre a SP02 em nova sessão SAP para preservar a F110 original.
    _notificar(
        progress_callback,
        "Abrindo ordens spool próprias...",
        97,
    )

    f110_session = focar_sessao(session)
    application = obter_aplicacao_da_sessao(f110_session)
    sessoes_antes = snapshot_sessoes(application)
    f110_id = identidade_sessao(f110_session)

    if not sessao_e_f110(
        f110_session,
        data_exec=data_exec,
        identificacao=identificacao,
    ):
        f110_recuperada = localizar_sessao_f110(
            application,
            data_exec=data_exec,
            identificacao=identificacao,
        )

        if f110_recuperada:
            f110_session = focar_sessao(f110_recuperada)
            f110_id = identidade_sessao(f110_session)
        elif logger:
            logger.add(
                6,
                "Sessão F110 original não confirmada antes da abertura da spool.",
                nivel="AVISO",
            )

    _abrir_transacao_nova_sessao(f110_session, "SP02")

    spool_session = aguardar_nova_sessao(
        application,
        sessoes_antes,
        predicado=sessao_e_spool,
        timeout=15,
    )

    if spool_session is None:
        spool_session = localizar_sessao_spool(
            application,
            ignorar_ids=set(sessoes_antes) | {f110_id},
        )

    if spool_session is None:
        if sessao_e_spool(f110_session):
            spool_session = f110_session
        else:
            raise RuntimeError(
                "A SP02 não abriu em uma nova sessão SAP e a F110 original foi preservada. "
                "Não foi possível localizar a tela de spool para gerar o boleto."
            )

    spool_abriu_nova_sessao = not mesma_sessao(spool_session, f110_session)
    focar_sessao(spool_session)

    if logger:
        logger.add(
            6,
            (
                "Ordens spool próprias abertas em nova sessão SAP."
                if spool_abriu_nova_sessao
                else "Ordens spool abertas na mesma sessão SAP."
            ),
            publico=True,
        )

    _notificar(
        progress_callback,
        "Ordens spool abertas. Gere o PDF no PDFCreator.",
        98,
    )

    return {
        "public": {
            "spool_boleto": "ABERTO",
            "spool_nova_sessao": spool_abriu_nova_sessao,
        },
        "f110_session": f110_session,
        "spool_session": spool_session,
        "spool_abriu_nova_sessao": spool_abriu_nova_sessao,
        "sessoes_antes": sessoes_antes,
    }


def fechar_spool_e_retornar_f110(
    contexto_spool,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    # Fecha somente a sessão da SP02 e devolve o controle para a F110 original.
    _notificar(
        progress_callback,
        "Fechando janela da spool e retomando F110...",
        99,
    )

    f110_session = contexto_spool.get("f110_session")
    spool_session = contexto_spool.get("spool_session")
    spool_abriu_nova_sessao = bool(contexto_spool.get("spool_abriu_nova_sessao"))

    if spool_session and spool_abriu_nova_sessao:
        if logger:
            logger.add(6, "Fechando somente a sessão SAP da SP02.", publico=True)

        fechar_popups_se_existirem(spool_session)

        if not fechar_sessao_principal(spool_session):
            raise RuntimeError("Não foi possível fechar a sessão SAP da SP02.")

    elif spool_session:
        # Fallback para ambientes onde a SP02 não abriu em nova sessão.
        # Aqui a F110 precisa ser reaberta no BOL correto para seguir com segurança.
        if logger:
            logger.add(
                6,
                "SP02 abriu na mesma sessão. Reabrindo F110 no BOL correto.",
                nivel="AVISO",
                publico=True,
            )

        abrir_f110_com_bol(
            spool_session,
            logger=logger,
            progress_callback=progress_callback,
            data_exec=data_exec,
            identificacao=identificacao,
        )
        f110_session = spool_session

    if f110_session is None:
        raise RuntimeError("Sessão F110 original ausente no contexto da spool.")

    application = obter_aplicacao_da_sessao(f110_session)

    if not sessao_e_f110(
        f110_session,
        data_exec=data_exec,
        identificacao=identificacao,
    ):
        f110_localizada = localizar_sessao_f110(
            application,
            data_exec=data_exec,
            identificacao=identificacao,
        )

        if not f110_localizada:
            raise RuntimeError(
                "A sessão F110 original não foi localizada após fechar a SP02."
            )

        f110_session = f110_localizada

    focar_sessao(f110_session)

    if logger:
        logger.add(6, "Controle devolvido para a F110 original.", publico=True)

    return f110_session


def _garantir_f110_no_bol(session, data_exec=None, identificacao=None, logger=None):
    # Reposiciona a sessao na F110/BOL correto antes de qualquer passo critico.
    if sessao_e_f110(
        session,
        data_exec=data_exec,
        identificacao=identificacao,
        exigir_campos=bool(data_exec or identificacao),
    ):
        return focar_sessao(session)

    if not data_exec:
        raise RuntimeError("Data da F110 nao informada.")

    if not identificacao:
        raise RuntimeError("Identificacao BOL nao informada.")

    if logger:
        logger.add(
            6,
            f"Reabrindo F110 no BOL {identificacao} antes de continuar.",
            publico=False,
        )

    focar_sessao(session)

    campo_ok = wait_for_element(
        session,
        "wnd[0]/tbar[0]/okcd",
        timeout=10,
    )
    campo_ok.text = "/nF110"
    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    campo_data = wait_for_element(
        session,
        "wnd[0]/usr/ctxtF110V-LAUFD",
        timeout=10,
    )
    campo_bol = wait_for_element(
        session,
        "wnd[0]/usr/ctxtF110V-LAUFI",
        timeout=10,
    )

    campo_data.text = str(data_exec)
    campo_bol.text = str(identificacao)
    session.findById("wnd[0]").sendVKey(0)
    wait_until_ready(session)

    return focar_sessao(session)


def _sessao_viva(session):
    try:
        session.findById("wnd[0]")
        return True
    except Exception:
        return False


def _fechar_popups_recuperacao(session):
    for _ in range(3):
        try:
            popup = session.findById("wnd[1]")
        except Exception:
            return

        for element_id in (
            "usr/btnSPOP-OPTION1",
            "usr/btnBUTTON_1",
            "tbar[0]/btn[0]",
            "tbar[0]/btn[12]",
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


def _enviar_vkey_recuperacao(session, vkey, descricao, logger=None):
    try:
        focar_sessao(session)
        _fechar_popups_recuperacao(session)
        session.findById("wnd[0]").sendVKey(vkey)
        wait_until_ready(session)
        _fechar_popups_recuperacao(session)

        if logger:
            logger.add(
                6,
                f"Recuperacao spool: {descricao} enviado.",
                publico=False,
            )

        return True
    except Exception as exc:
        if logger:
            logger.add(
                6,
                f"Recuperacao spool: falha ao enviar {descricao}: {exc}",
                nivel="AVISO",
                publico=False,
            )

        return False


def _sessoes_candidatas_recuperacao(application, spool_id=None, f110_id=None):
    candidatas = []
    vistos = set()

    for session in (
        localizar_sessao_por_id(application, spool_id) if spool_id else None,
        localizar_sessao_spool(application, ignorar_ids={f110_id} if f110_id else None),
    ):
        if session is None:
            continue

        session_id = identidade_sessao(session)

        if session_id not in vistos and _sessao_viva(session):
            candidatas.append(session)
            vistos.add(session_id)

    for session in iterar_sessoes_sap(application):
        try:
            session_id = identidade_sessao(session)

            if session_id in vistos:
                continue

            if f110_id and session_id == f110_id:
                continue

            if _sessao_viva(session):
                candidatas.append(session)
                vistos.add(session_id)
        except Exception:
            continue

    if f110_id:
        f110_session = localizar_sessao_por_id(application, f110_id)

        if f110_session is not None and identidade_sessao(f110_session) not in vistos:
            candidatas.append(f110_session)

    return candidatas


def _tentar_sair_spool_por_teclas(
    application,
    spool_id=None,
    f110_id=None,
    logger=None,
    progress_callback=None,
):
    _notificar(
        progress_callback,
        "Tentando recuperar janela SAP por teclas...",
        99,
    )

    sequencia = (
        (12, "F12"),
        (15, "Shift+F3"),
        (3, "F3"),
    )

    if localizar_sessao_spool(
        application,
        ignorar_ids={f110_id} if f110_id else None,
    ) is None:
        return True

    for rodada in range(1, 5):
        for session in _sessoes_candidatas_recuperacao(
            application,
            spool_id=spool_id,
            f110_id=f110_id,
        ):
            if not _sessao_viva(session):
                continue

            if logger:
                logger.add(
                    6,
                    f"Recuperacao spool rodada {rodada}: {fingerprint_sessao(session)}",
                    publico=False,
                )

            for vkey, descricao in sequencia:
                _enviar_vkey_recuperacao(
                    session,
                    vkey,
                    descricao,
                    logger=logger,
                )

                if localizar_sessao_spool(
                    application,
                    ignorar_ids={f110_id} if f110_id else None,
                ) is None:
                    return True

    return localizar_sessao_spool(
        application,
        ignorar_ids={f110_id} if f110_id else None,
    ) is None


def _obter_sessao_para_reabrir_f110(application, f110_id=None):
    if f110_id:
        f110_session = localizar_sessao_por_id(application, f110_id)

        if f110_session is not None:
            return f110_session

    f110_session = localizar_sessao_f110(application)

    if f110_session is not None:
        return f110_session

    for session in iterar_sessoes_sap(application):
        try:
            if _sessao_viva(session) and not sessao_e_spool(session):
                return session
        except Exception:
            continue

    for session in iterar_sessoes_sap(application):
        try:
            if _sessao_viva(session):
                return session
        except Exception:
            continue

    return None


# Implementacao robusta: esta definicao substitui a anterior e evita cachear
# sessoes COM depois que a SP02 altera a topologia do SAP GUI.
def abrir_ordens_spool_boleto_em_nova_sessao(
    session,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    _notificar(
        progress_callback,
        "Abrindo ordens spool proprias...",
        97,
    )

    application = obter_aplicacao_da_sessao(session)
    dump_sessoes(application, logger=logger, label="ANTES_SP02")

    f110_session = localizar_sessao_f110(
        application,
        data_exec=data_exec,
        identificacao=identificacao,
        exigir_campos=True,
    )

    if f110_session is None:
        f110_session = localizar_sessao_f110(
            application,
            data_exec=data_exec,
            identificacao=identificacao,
        )

    if f110_session is None:
        f110_session = session

    f110_session = _garantir_f110_no_bol(
        f110_session,
        data_exec=data_exec,
        identificacao=identificacao,
        logger=logger,
    )

    sessoes_antes = snapshot_sessoes(application)
    quantidade_antes = contar_sessoes(application)
    f110_id = identidade_sessao(f110_session)

    if logger:
        logger.add(
            6,
            f"F110 base antes da SP02: {fingerprint_sessao(f110_session)}",
            publico=False,
        )

    _abrir_transacao_nova_sessao(f110_session, "SP02")

    aguardar_quantidade_sessoes(
        application,
        quantidade_antes + 1,
        timeout=6,
    )

    spool_session = aguardar_nova_sessao(
        application,
        sessoes_antes,
        predicado=sessao_e_spool,
        timeout=15,
    )

    if spool_session is None:
        spool_session = localizar_sessao_spool(
            application,
            ignorar_ids=set(sessoes_antes) | {f110_id},
        )

    if spool_session is None and sessao_e_spool(f110_session):
        spool_session = f110_session

    if spool_session is None:
        dump_sessoes(application, logger=logger, label="SP02_NAO_LOCALIZADA")
        raise RuntimeError(
            "Nao foi possivel localizar a sessao SP02/spool apos abertura."
        )

    spool_abriu_nova_sessao = not mesma_sessao(spool_session, f110_session)
    spool_id = identidade_sessao(spool_session)
    focar_sessao(spool_session)

    if logger:
        logger.add(
            6,
            (
                "Ordens spool proprias abertas em nova sessao SAP."
                if spool_abriu_nova_sessao
                else "Ordens spool abertas na mesma sessao SAP."
            ),
            publico=True,
        )
        logger.add(
            6,
            f"SP02 localizada: {fingerprint_sessao(spool_session)}",
            publico=False,
        )
        dump_sessoes(application, logger=logger, label="APOS_ABRIR_SP02")

    _notificar(
        progress_callback,
        "Ordens spool abertas. Gere o PDF no PDFCreator.",
        98,
    )

    return {
        "public": {
            "spool_boleto": "ABERTO",
            "spool_nova_sessao": spool_abriu_nova_sessao,
        },
        "application": application,
        "f110_id": f110_id,
        "spool_id": spool_id,
        "spool_abriu_nova_sessao": spool_abriu_nova_sessao,
        "sessoes_antes": sessoes_antes,
        "quantidade_antes": quantidade_antes,
    }


def fechar_spool_e_retornar_f110(
    contexto_spool,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    _notificar(
        progress_callback,
        "Fechando janela da spool e retomando F110...",
        99,
    )

    application = contexto_spool.get("application")
    f110_id = contexto_spool.get("f110_id")
    spool_id = contexto_spool.get("spool_id")
    quantidade_antes = contexto_spool.get("quantidade_antes")
    spool_abriu_nova_sessao = bool(contexto_spool.get("spool_abriu_nova_sessao"))

    if application is None:
        raise RuntimeError("Aplicacao SAP ausente no contexto da spool.")

    dump_sessoes(application, logger=logger, label="ANTES_FECHAR_SP02")

    spool_session = None

    if spool_id:
        spool_session = localizar_sessao_por_id(application, spool_id)

    if spool_session is None:
        spool_session = localizar_sessao_spool(
            application,
            ignorar_ids={f110_id} if f110_id else None,
        )

    if spool_session and spool_abriu_nova_sessao:
        if logger:
            logger.add(
                6,
                f"Fechando somente a sessao SP02: {fingerprint_sessao(spool_session)}",
                publico=True,
            )

        fechar_popups_se_existirem(spool_session)

        if not fechar_sessao_principal(spool_session):
            if logger:
                logger.add(
                    6,
                    "Fechamento direto da SP02 falhou. Acionando recuperacao por F12/Shift+F3.",
                    nivel="AVISO",
                    publico=True,
                )

            _tentar_sair_spool_por_teclas(
                application,
                spool_id=spool_id,
                f110_id=f110_id,
                logger=logger,
                progress_callback=progress_callback,
            )

    elif spool_session:
        if logger:
            logger.add(
                6,
                "SP02 abriu na mesma sessao. Reposicionando F110 no BOL correto.",
                nivel="AVISO",
                publico=True,
            )

        return _garantir_f110_no_bol(
            spool_session,
            data_exec=data_exec,
            identificacao=identificacao,
            logger=logger,
        )
    elif logger:
        logger.add(
            6,
            "Sessao SP02 nao localizada apos PDF. Tentando retomar F110 pela raiz.",
            nivel="AVISO",
            publico=True,
        )

    if quantidade_antes:
        aguardar_quantidade_sessoes(
            application,
            quantidade_antes,
            timeout=10,
        )

    dump_sessoes(application, logger=logger, label="APOS_FECHAR_SP02")

    f110_session = localizar_sessao_f110(
        application,
        data_exec=data_exec,
        identificacao=identificacao,
        exigir_campos=True,
    )

    if f110_session is None and f110_id:
        f110_session = localizar_sessao_por_id(application, f110_id)

    if f110_session is None:
        f110_session = _obter_sessao_para_reabrir_f110(
            application,
            f110_id=f110_id,
        )

    if f110_session is None:
        raise RuntimeError("Nao foi possivel localizar a sessao F110 apos fechar a SP02.")

    f110_session = _garantir_f110_no_bol(
        f110_session,
        data_exec=data_exec,
        identificacao=identificacao,
        logger=logger,
    )

    if logger:
        logger.add(
            6,
            f"Controle devolvido para a F110: {fingerprint_sessao(f110_session)}",
            publico=True,
        )

    return f110_session


def sair_spool_com_f12(
    session,
    logger=None,
    progress_callback=None,
):
    # Saída validada no SAP real para destravar a navegação após o PDFCreator.
    _notificar(
        progress_callback,
        "Saindo da tela de spool com F12...",
        98,
    )

    try:
        fechar_popups_se_existirem(session)

        for _ in range(3):
            try:
                session.findById("wnd[0]").sendVKey(12)
                wait_until_ready(session)
                fechar_popups_se_existirem(session)
            except Exception:
                pass

        if logger:
            logger.add(
                6,
                "Tentativa de saída da spool com F12 concluída.",
                publico=True,
            )

    except Exception as e:
        raise RuntimeError(f"Erro ao sair da tela de spool com F12: {e}") from e


def voltar_tela_inicial_com_f3(
    session,
    logger=None,
    progress_callback=None,
):
    # Mantido como fallback: tenta voltar por OKCODE /n e, se necessário, F3.
    _notificar(
        progress_callback,
        "Voltando da tela do boleto...",
        98,
    )

    try:
        fechar_popups_se_existirem(session)
        voltou = False

        for _ in range(4):
            try:
                campo_ok = session.findById("wnd[0]/tbar[0]/okcd")
                campo_ok.text = "/n"
                session.findById("wnd[0]").sendVKey(0)
                wait_until_ready(session)
                voltou = True
                break
            except Exception:
                try:
                    session.findById("wnd[0]").sendVKey(3)
                    wait_until_ready(session)
                    fechar_popups_se_existirem(session)
                except Exception:
                    pass

        if not voltou:
            try:
                session.findById("wnd[0]").sendVKey(3)
                wait_until_ready(session)
                fechar_popups_se_existirem(session)
            except Exception:
                pass

    except Exception as e:
        raise RuntimeError(f"Erro ao voltar da tela do boleto: {e}") from e

    if logger:
        logger.add(
            6,
            "Retornou da tela de spool/tela de boleto.",
            publico=True,
        )


def abrir_f110_com_bol(
    session,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    # Reabre diretamente a F110 no BOL criado antes de baixar o meio de pagamento.
    if not data_exec:
        raise RuntimeError("Data da F110 não informada.")

    if not identificacao:
        raise RuntimeError("Identificação BOL não informada.")

    _notificar(
        progress_callback,
        f"Reabrindo F110 no {identificacao}...",
        99,
    )

    try:
        fechar_popups_se_existirem(session)

        campo_ok = wait_for_element(
            session,
            "wnd[0]/tbar[0]/okcd",
            timeout=10,
        )
        campo_ok.text = "/nF110"

        session.findById("wnd[0]").sendVKey(0)
        wait_until_ready(session)

        campo_data = wait_for_element(
            session,
            "wnd[0]/usr/ctxtF110V-LAUFD",
            timeout=10,
        )
        campo_bol = wait_for_element(
            session,
            "wnd[0]/usr/ctxtF110V-LAUFI",
            timeout=10,
        )

        campo_data.text = str(data_exec)
        campo_bol.text = str(identificacao)

        session.findById("wnd[0]").sendVKey(0)
        wait_until_ready(session)

    except Exception as e:
        raise RuntimeError(f"Erro ao reabrir F110 no {identificacao}: {e}") from e

    if logger:
        logger.add(
            6,
            f"F110 reaberta no {identificacao}.",
            publico=True,
        )

    _notificar(
        progress_callback,
        f"F110 reaberta no {identificacao}.",
        99,
    )

    return {
        "f110_reaberta": "OK",
    }


def baixar_arquivo_meio_pagamento(
    session,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    # Fluxo validado: Ambiente > Meio pagamento > IDS, F8, F7, F4 e confirma.
    _notificar(
        progress_callback,
        "Abrindo meio de pagamento...",
        99,
    )

    try:
        wait_for_element(
            session,
            "wnd[0]",
            timeout=10,
        ).maximize()
        wait_until_ready(session)

        fechar_popups_se_existirem(session)

        wait_for_element(
            session,
            "wnd[0]/mbar/menu[3]/menu[6]/menu[0]",
            timeout=10,
        ).select()
        wait_until_ready(session)

        session.findById("wnd[0]").sendVKey(19)
        wait_until_ready(session)

        session.findById("wnd[0]").sendVKey(18)
        wait_until_ready(session)

        wait_for_element(
            session,
            "wnd[1]",
            timeout=10,
        ).sendVKey(4)
        wait_until_ready(session)

        wait_for_element(
            session,
            "wnd[1]/tbar[0]/btn[0]",
            timeout=10,
        ).press()
        wait_until_ready(session)

        session.findById("wnd[0]").sendVKey(3)
        wait_until_ready(session)

        session.findById("wnd[0]").sendVKey(3)
        wait_until_ready(session)

    except Exception as e:
        _notificar(
            progress_callback,
            f"Erro no meio de pagamento: {e}",
            99,
            status="erro",
        )

        raise RuntimeError(f"Erro ao gerar meio de pagamento: {e}") from e

    if logger:
        logger.add(
            6,
            "Meio de pagamento confirmado e retorno à tela inicial concluído.",
            publico=True,
        )

    _notificar(
        progress_callback,
        "Meio de pagamento concluído.",
        100,
    )

    return {
        "arquivo_meio_pagamento": "CONFIRMADO",
    }


def finalizar_boleto_f110(
    session,
    logger=None,
    progress_callback=None,
    dados=None,
    cliente=None,
    numero_boleto=None,
    data_exec=None,
    identificacao=None,
):
    # Finaliza boleto/remessa após execução da F110.
    resultado = {}

    contexto_spool = abrir_ordens_spool_boleto_em_nova_sessao(
        session,
        logger=logger,
        progress_callback=progress_callback,
        data_exec=data_exec,
        identificacao=identificacao,
    )
    resultado.update(contexto_spool["public"])

    nome_pdf_sugerido = montar_nome_pdf_sugerido(
        numero_boleto,
        dados=dados,
        cliente=cliente,
    )
    resultado["nome_pdf_sugerido"] = nome_pdf_sugerido

    _notificar(
        progress_callback,
        "Aguardando confirmação do PDF...",
        98,
    )

    try:
        confirmar_pdf_boleto(nome_pdf_sugerido)
    except Exception:
        _notificar(
            progress_callback,
            "PDF não confirmado pelo usuário.",
            98,
            status="erro",
        )
        raise

    resultado["pdf_boleto"] = "CONFIRMADO"

    f110_session = fechar_spool_e_retornar_f110(
        contexto_spool,
        logger=logger,
        progress_callback=progress_callback,
        data_exec=data_exec,
        identificacao=identificacao,
    )

    resultado.update(
        baixar_arquivo_meio_pagamento(
            f110_session,
            logger=logger,
            progress_callback=progress_callback,
            data_exec=data_exec,
            identificacao=identificacao,
        )
    )

    return resultado
