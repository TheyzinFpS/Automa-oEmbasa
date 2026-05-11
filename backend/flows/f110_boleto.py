import ctypes
import re

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
    # Abre transação SAP utilizando OKCODE.
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
    mensagem = _mensagem_confirmacao_pdf(nome_pdf_sugerido)

    resposta = ctypes.windll.user32.MessageBoxW(
        None,
        mensagem,
        "EMBASA - Confirmação do boleto",
        _MB_YESNO | _MB_ICONQUESTION | _MB_TOPMOST,
    )

    if resposta != _IDYES:
        raise RuntimeError(
            "Geração do PDF do boleto não confirmada pelo usuário."
        )


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

    status_var = tk.StringVar(
        value="Clique em Copiar nome para usar no PDFCreator."
    )
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
        raise RuntimeError(
            "Geração do PDF do boleto não confirmada pelo usuário."
        )


def abrir_ordens_spool_boleto(
    session,
    logger=None,
    progress_callback=None,
):
    # Abre SP02 para impressão do boleto.
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


def voltar_tela_inicial_com_f3(
    session,
    logger=None,
    progress_callback=None,
):
    # Retorna da SP02 utilizando F3.
    _notificar(
        progress_callback,
        "Voltando da tela do boleto...",
        98,
    )

    try:
        session.findById("wnd[0]").sendVKey(3)
        wait_until_ready(session)
    except Exception as e:
        raise RuntimeError(
            f"Erro ao voltar da tela do boleto: {e}"
        ) from e

    if logger:
        logger.add(
            6,
            "Retornou da tela de spool utilizando F3.",
            publico=True,
        )


def abrir_f110_com_bol(
    session,
    logger=None,
    progress_callback=None,
    data_exec=None,
    identificacao=None,
):
    # Reabre a F110 utilizando o BOL correto.
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
    # Fluxo final validado do meio de pagamento:
    # 1. Ambiente > Meio de pagamento > Dados administrativos IDS
    # 2. F8
    # 3. F7
    # 4. F4 para selecionar/salvar arquivo
    # 5. Confirmar download
    # 6. F3
    # 7. F3
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

        wait_for_element(
            session,
            "wnd[0]/mbar/menu[3]/menu[6]/menu[0]",
            timeout=10,
        ).select()
        wait_until_ready(session)

        # Sequência gravada/validada no SAP GUI para avançar no suporte de dados.
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

        raise RuntimeError(
            f"Erro ao gerar meio de pagamento: {e}"
        ) from e

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
    # Fluxo final completo da F110:
    # 1. SP02
    # 2. Geração manual PDF
    # 3. F3
    # 4. Reabre F110
    # 5. Reentra no BOL
    # 6. Meio de pagamento
    # 7. Confirma download
    # 8. Retorna à tela inicial
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
