import ctypes
import re
import time

from backend.documentos import formatar_doc
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
    # Mantém a automação na mesma sessão SAP. Isso evita a perda de controle
    # causada pela abertura da SP02 em uma segunda janela via /oSP02.
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


def _notificar(progress_callback, mensagem, percentual, status="processando"):
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
    resposta = ctypes.windll.user32.MessageBoxW(
        None,
        _mensagem_confirmacao_pdf(nome_pdf_sugerido),
        "EMBASA - Confirmação do boleto",
        _MB_YESNO | _MB_ICONQUESTION | _MB_TOPMOST,
    )

    if resposta != _IDYES:
        raise RuntimeError("Geração do PDF do boleto não confirmada pelo usuário.")


def confirmar_pdf_boleto(nome_pdf_sugerido):
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


def _texto_seguro(valor):
    try:
        return str(valor or "").strip()
    except Exception:
        return ""


def _transacao_atual(session):
    try:
        return _texto_seguro(session.Info.Transaction).upper()
    except Exception:
        return ""


def _titulo_janela_atual(session):
    try:
        return _texto_seguro(session.findById("wnd[0]").text).upper()
    except Exception:
        try:
            return _texto_seguro(session.findById("wnd[0]").Text).upper()
        except Exception:
            return ""


def _esta_na_sp02(session):
    # Identifica a SP02 tanto pela transação quanto pelo título da janela.
    transacao = _transacao_atual(session)
    titulo = _titulo_janela_atual(session)

    if transacao in {"SP01", "SP02"}:
        return True

    marcadores = (
        "CONTROLE DE SA",
        "SPOOL",
        "ORDENS SPOOL",
        "SINTESE DAS ORDENS",
        "SÍNTESE DAS ORDENS",
    )

    return any(marcador in titulo for marcador in marcadores)


def _focar_janela_sp02(session):
    # Reforça o foco antes do fallback com F12, sem depender do foco visual do Windows.
    janela = wait_for_element(session, "wnd[0]", timeout=5)

    try:
        janela.maximize()
    except Exception:
        pass

    for element_id in ("wnd[0]", "wnd[0]/usr"):
        try:
            elemento = session.findById(element_id)
            elemento.setFocus()
            break
        except Exception:
            try:
                elemento.SetFocus()
                break
            except Exception:
                continue

    wait_until_ready(session)


def _aguardar_saida_sp02(session, timeout=2):
    deadline = time.monotonic() + max(0.2, float(timeout or 0.2))

    while time.monotonic() < deadline:
        wait_until_ready(session, timeout=1)

        if not _esta_na_sp02(session):
            return True

        time.sleep(0.15)

    return not _esta_na_sp02(session)


def _fallback_sair_sp02_com_f12(session, logger=None, tentativas=4):
    for tentativa in range(1, int(tentativas or 1) + 1):
        try:
            _focar_janela_sp02(session)
            session.findById("wnd[0]").sendVKey(12)
            wait_until_ready(session)
            fechar_popups_se_existirem(session, max_tentativas=2)

            if _aguardar_saida_sp02(session, timeout=1.5):
                if logger:
                    logger.add(
                        6,
                        f"Saiu da SP02 usando F12 no fallback ({tentativa}/{tentativas}).",
                        publico=True,
                    )
                return True

        except Exception as exc:
            if logger:
                logger.add(
                    6,
                    f"Fallback F12 na SP02 falhou ({tentativa}/{tentativas}): {exc}",
                    nivel="AVISO",
                    publico=False,
                )

    return False


def abrir_ordens_spool_boleto(
    session,
    logger=None,
    progress_callback=None,
):
    # Abre a SP02 na mesma sessão SAP para evitar criação de segunda janela.
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
        "spool_nova_sessao": False,
    }


def voltar_tela_inicial_com_f3(
    session,
    logger=None,
    progress_callback=None,
):
    # Retorna da tela da SP02 antes de reabrir a F110 no BOL correto.
    _notificar(
        progress_callback,
        "Voltando da tela do boleto...",
        98,
    )

    try:
        session.findById("wnd[0]").sendVKey(3)
        wait_until_ready(session)

    except Exception as exc:
        raise RuntimeError(f"Erro ao voltar da tela do boleto: {exc}") from exc

    if _aguardar_saida_sp02(session, timeout=2):
        if logger:
            logger.add(
                6,
                "Retornou da tela de spool utilizando F3.",
                publico=True,
            )
        return

    if logger:
        logger.add(
            6,
            "F3 não saiu da SP02. Tentando fallback com F12.",
            nivel="AVISO",
            publico=True,
        )

    if not _fallback_sair_sp02_com_f12(session, logger=logger):
        raise RuntimeError("Não foi possível sair da SP02 após F3 e fallback com F12.")

    if logger:
        logger.add(
            6,
            "Retornou da tela de spool após fallback.",
            publico=True,
        )


def abrir_f110_com_bol(
    session,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    if not data_exec:
        raise RuntimeError("Data da F110 não informada.")

    if not identificacao:
        raise RuntimeError("Identificação BOL não informada.")

    _notificar(
        progress_callback,
        f"Reabrindo F110 no {identificacao}...",
        99,
    )

    _abrir_transacao(
        session,
        "F110",
        wait_id="wnd[0]/usr",
        timeout=12,
    )

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
    # Fluxo validado via VBS:
    # Ambiente > Meio de pagamento > Dados administrativos IDS > F8 > F7
    # > F4 > confirmar download > F3 > F3.
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

    except Exception as exc:
        _notificar(
            progress_callback,
            f"Erro no meio de pagamento: {exc}",
            99,
            status="erro",
        )

        raise RuntimeError(f"Erro ao gerar meio de pagamento: {exc}") from exc

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
    # Fluxo final da F110:
    # 1. Abre SP02 na mesma sessão
    # 2. Usuário gera o PDF
    # 3. Retorna com F3
    # 4. Reabre F110 no BOL
    # 5. Gera/baixa o meio de pagamento
    resultado = {}

    resultado.update(
        abrir_ordens_spool_boleto(
            session,
            logger=logger,
            progress_callback=progress_callback,
        )
    )

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

    voltar_tela_inicial_com_f3(
        session,
        logger=logger,
        progress_callback=progress_callback,
    )

    resultado.update(
        abrir_f110_com_bol(
            session,
            logger=logger,
            progress_callback=progress_callback,
            data_exec=data_exec,
            identificacao=identificacao,
        )
    )

    resultado.update(
        baixar_arquivo_meio_pagamento(
            session,
            logger=logger,
            progress_callback=progress_callback,
            data_exec=data_exec,
            identificacao=identificacao,
        )
    )

    return resultado
