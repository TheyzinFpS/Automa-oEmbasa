import re
import time
import unicodedata

from backend.documentos import formatar_doc
from backend.utils.sap_waits import wait_for_element, wait_until_ready


_TIPOS_LABEL = {
    "viabilidade": "Viabilidade",
    "agua": "Projeto Água",
    "esgoto": "Projeto Esgoto",
}

_CELL_ID_RE = re.compile(r"/(?P<tipo>lbl|txt|chk)\[(?P<x>\d+),(?P<y>\d+)\]$")
_DATA_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
_HORA_RE = re.compile(r"\b\d{2}:\d{2}\b")
_SPOOL_RE = re.compile(r"^\d{5,}$")


def _abrir_transacao(session, codigo, wait_id="wnd[0]/usr", timeout=10):
    # Mantém a automação na mesma sessão SAP. Para este fluxo, a SP02 deve ser
    # aberta por /nSP02, evitando a segunda janela que causava perda de controle.
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


def _texto_seguro(valor):
    try:
        return str(valor or "").strip()
    except Exception:
        return ""


def _normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", _texto_seguro(valor))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip().upper()


def _safe_getattr(objeto, *nomes, default=""):
    for nome in nomes:
        try:
            valor = getattr(objeto, nome)
        except Exception:
            continue

        if valor is not None:
            return valor

    return default


def _texto_elemento(elemento):
    return _texto_seguro(_safe_getattr(elemento, "Text", "text", default=""))


def _id_elemento(elemento):
    return _texto_seguro(_safe_getattr(elemento, "Id", "id", default=""))


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


def _copiar_nome_pdf(nome_pdf_sugerido):
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(nome_pdf_sugerido)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


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


def _iterar_filhos(container, profundidade=0, limite=5):
    if profundidade > limite:
        return

    try:
        filhos = container.Children
        total = int(filhos.Count)
    except Exception:
        return

    for indice in range(total):
        try:
            filho = filhos(indice)
        except Exception:
            continue

        yield filho
        yield from _iterar_filhos(filho, profundidade + 1, limite)


def _componentes_usuario(session, recursivo=False):
    container = wait_for_element(session, "wnd[0]/usr", timeout=10)

    if recursivo:
        return list(_iterar_filhos(container))

    try:
        filhos = container.Children
        return [filhos(indice) for indice in range(int(filhos.Count))]
    except Exception:
        return []


def _montar_linha_sp02(numero_linha, dados):
    textos = [
        item
        for item in dados.get("cells", [])
        if item.get("text")
    ]
    textos.sort(key=lambda item: item.get("x", 0))

    texto_completo = " ".join(item["text"] for item in textos)
    texto_normalizado = _normalizar_texto(texto_completo)

    titulo_item = None
    for item in textos:
        item_norm = _normalizar_texto(item["text"])
        if "BOLETO" in item_norm or "NOTA ACOMPANH" in item_norm:
            titulo_item = item
            break

    if titulo_item is None:
        for item in reversed(textos):
            texto = item.get("text", "")
            if any(ch.isalpha() for ch in texto):
                titulo_item = item
                break

    spool = ""
    data = ""
    hora = ""
    paginas = ""
    status = ""

    for item in textos:
        texto = item.get("text", "")
        texto_norm = _normalizar_texto(texto)

        if not spool and _SPOOL_RE.match(texto):
            spool = texto
            continue

        if not data:
            data_match = _DATA_RE.search(texto)
            if data_match:
                data = data_match.group(0)
                continue

        if not hora:
            hora_match = _HORA_RE.search(texto)
            if hora_match:
                hora = hora_match.group(0)
                continue

        if not status and texto_norm in {"-", "CONCL.", "CONCL", "ESPERA"}:
            status = texto
            continue

        if not paginas and texto.isdigit() and len(texto) <= 3 and texto != spool:
            paginas = texto

    return {
        "linha": numero_linha,
        "spool": spool,
        "data": data,
        "hora": hora,
        "status": status,
        "paginas": paginas,
        "titulo": titulo_item.get("text", "") if titulo_item else "",
        "titulo_id": titulo_item.get("id", "") if titulo_item else "",
        "checkbox_id": dados.get("checkbox_id", ""),
        "texto": texto_completo,
        "texto_normalizado": texto_normalizado,
    }


def _numero_spool_int(linha):
    try:
        return int(str(linha.get("spool") or "0").strip())
    except Exception:
        return 0


def _ordenar_linhas_sp02_decrescente(linhas):
    # A SP02 costuma exibir as spools mais recentes no topo, mas a ordenação
    # por número garante que a verificação sempre priorize a spool mais nova.
    return sorted(
        linhas,
        key=lambda linha: (
            _numero_spool_int(linha),
            -int(linha.get("linha") or 0),
        ),
        reverse=True,
    )


def _coletar_linhas_sp02(session):
    linhas = {}

    for elemento in _componentes_usuario(session):
        elemento_id = _id_elemento(elemento)
        match = _CELL_ID_RE.search(elemento_id)

        if not match:
            continue

        tipo = match.group("tipo")
        x = int(match.group("x"))
        y = int(match.group("y"))
        linha = linhas.setdefault(y, {"cells": [], "checkbox_id": ""})

        if tipo == "chk":
            linha["checkbox_id"] = elemento_id
            continue

        texto = _texto_elemento(elemento)
        if texto:
            linha["cells"].append(
                {
                    "id": elemento_id,
                    "x": x,
                    "y": y,
                    "text": texto,
                }
            )

    linhas_montadas = [
        _montar_linha_sp02(numero_linha, dados)
        for numero_linha, dados in sorted(linhas.items())
    ]

    linhas_validas = [
        linha
        for linha in linhas_montadas
        if linha["spool"] or linha["titulo"] or "BOLETO" in linha["texto_normalizado"]
    ]

    return _ordenar_linhas_sp02_decrescente(linhas_validas)


def _linha_e_boleto(linha):
    texto = linha.get("texto_normalizado", "")
    return "BOLETO" in texto and "CONTAS A RECEBER" in texto


def _linha_e_nota_acompanhamento(linha):
    texto = linha.get("texto_normalizado", "")
    return "NOTA ACOMPANH" in texto


def _localizar_par_spool_sp02(session):
    linhas = _coletar_linhas_sp02(session)
    notas = _ordenar_linhas_sp02_decrescente(
        [linha for linha in linhas if _linha_e_nota_acompanhamento(linha)]
    )
    por_linha = {linha["linha"]: linha for linha in linhas}

    for nota in notas:
        boleto = por_linha.get(nota["linha"] + 1)
        if boleto and _linha_e_boleto(boleto):
            return nota, boleto

    boletos = _ordenar_linhas_sp02_decrescente(
        [linha for linha in linhas if _linha_e_boleto(linha)]
    )

    for boleto in boletos:
        nota = por_linha.get(boleto["linha"] - 1)
        if nota and _linha_e_nota_acompanhamento(nota):
            return nota, boleto

    resumo = "; ".join(
        linha.get("texto", "")
        for linha in linhas[:8]
        if linha.get("texto")
    )
    raise RuntimeError(
        "Nenhum par válido 'Nota acompanh.ISD &' seguido de "
        "'BOLETO (CONTAS A RECEBER)' foi encontrado. "
        f"Primeiras linhas lidas: {resumo or 'nenhuma'}."
    )


def _focar_elemento(session, element_id, caret_position=0):
    if not element_id:
        return False

    elemento = session.findById(element_id)

    try:
        elemento.setFocus()
    except Exception:
        try:
            elemento.SetFocus()
        except Exception:
            pass

    try:
        elemento.caretPosition = int(caret_position or 0)
    except Exception:
        pass

    return True


def _focar_linha_spool(session, linha):
    titulo_id = linha.get("titulo_id")
    if titulo_id:
        return _focar_elemento(session, titulo_id, caret_position=2)

    checkbox_id = linha.get("checkbox_id")
    if checkbox_id:
        return _focar_elemento(session, checkbox_id)

    raise RuntimeError(
        f"Não foi possível focar a linha da spool {linha.get('spool') or linha.get('linha')}."
    )


def _coletar_textos_tela(session):
    textos = []

    for elemento in _componentes_usuario(session, recursivo=True):
        texto = _texto_elemento(elemento)
        if texto:
            textos.append(texto)

    return textos


def _tela_contem(textos, valor):
    valor_norm = _normalizar_texto(valor)

    if not valor_norm:
        return True

    return any(valor_norm in _normalizar_texto(texto) for texto in textos)


def _checkbox_encerrado_marcado(session):
    for elemento in _componentes_usuario(session, recursivo=True):
        elemento_id = _id_elemento(elemento)
        texto = _texto_elemento(elemento)
        texto_norm = _normalizar_texto(f"{elemento_id} {texto}")

        if "ENCERRADO" not in texto_norm and "ANEXAR" not in texto_norm:
            continue

        if "/CHK" not in elemento_id.upper() and "GUICHECKBOX" not in _normalizar_texto(
            _safe_getattr(elemento, "Type", "type", default="")
        ):
            continue

        try:
            return bool(elemento.selected)
        except Exception:
            try:
                return bool(elemento.Selected)
            except Exception:
                return False

    return None


def _validar_detalhes_spool(session, linha, logger=None):
    _focar_linha_spool(session, linha)
    session.findById("wnd[0]").sendVKey(2)
    wait_until_ready(session)

    try:
        textos = _coletar_textos_tela(session)
        numero_detalhe = ""

        try:
            numero_detalhe = _texto_elemento(
                session.findById("wnd[0]/usr/txtTSP01_SP0R-RQID_CHAR")
            )
        except Exception:
            pass

        if linha.get("spool"):
            if numero_detalhe and numero_detalhe != linha["spool"]:
                raise RuntimeError(
                    "Detalhe da spool divergente: "
                    f"lista={linha['spool']} detalhe={numero_detalhe}."
                )

            if not numero_detalhe and not _tela_contem(textos, linha["spool"]):
                raise RuntimeError(
                    f"Detalhe da spool não confirmou o número {linha['spool']}."
                )

        for campo in ("titulo", "data", "hora"):
            valor = linha.get(campo)
            if valor and not _tela_contem(textos, valor):
                raise RuntimeError(
                    f"Detalhe da spool não confirmou {campo}: {valor}."
                )

        encerrado = _checkbox_encerrado_marcado(session)
        if encerrado is True:
            raise RuntimeError(
                "A spool do boleto está marcada como encerrada/já anexada. "
                "Impressão interrompida para evitar reprocessamento."
            )

        if logger and encerrado is None:
            logger.add(
                6,
                "Checkbox de encerramento da spool não localizado; validação seguiu pelos dados visíveis.",
                nivel="AVISO",
                publico=False,
            )

        return {
            "spool_numero": linha.get("spool", ""),
            "spool_titulo": linha.get("titulo", ""),
            "spool_data": linha.get("data", ""),
            "spool_hora": linha.get("hora", ""),
            "spool_encerrado": bool(encerrado),
        }

    finally:
        try:
            session.findById("wnd[0]").sendVKey(12)
            wait_until_ready(session)
        except Exception:
            pass


def _imprimir_spool_selecionada(session):
    session.findById("wnd[0]").sendVKey(44)
    wait_until_ready(session, timeout=12)


def _prefixar_dados_spool(prefixo, dados_spool):
    return {
        f"{prefixo}_{chave}": valor
        for chave, valor in dados_spool.items()
    }


def _transacao_atual(session):
    try:
        return _texto_seguro(session.Info.Transaction).upper()
    except Exception:
        return ""


def _titulo_janela_atual(session):
    try:
        return _texto_elemento(session.findById("wnd[0]")).upper()
    except Exception:
        return ""


def _esta_na_sp02(session):
    transacao = _transacao_atual(session)
    titulo = _normalizar_texto(_titulo_janela_atual(session))

    if transacao in {"SP01", "SP02"}:
        return True

    marcadores = (
        "CONTROLE DE SA",
        "SPOOL",
        "ORDENS SPOOL",
        "SINTESE DAS ORDENS",
    )

    return any(marcador in titulo for marcador in marcadores)


def _aguardar_saida_sp02(session, timeout=2):
    deadline = time.monotonic() + max(0.2, float(timeout or 0.2))

    while time.monotonic() < deadline:
        wait_until_ready(session, timeout=1)

        if not _esta_na_sp02(session):
            return True

        time.sleep(0.15)

    return not _esta_na_sp02(session)


def abrir_ordens_spool_boleto(
    session,
    logger=None,
    progress_callback=None,
):
    _notificar(progress_callback, "Abrindo ordens spool próprias...", 97)

    _abrir_transacao(
        session,
        "SP02",
        wait_id="wnd[0]/usr",
        timeout=12,
    )

    linhas = _coletar_linhas_sp02(session)
    if not linhas:
        raise RuntimeError("SP02 aberta, mas nenhuma linha de spool foi lida.")

    if logger:
        logger.add(6, "Ordens spool próprias abertas.", publico=True)

    _notificar(progress_callback, "SP02 aberta. Localizando boleto...", 97)

    return {
        "spool_boleto": "ABERTO",
        "spool_nova_sessao": False,
    }


def voltar_tela_inicial_com_f3(
    session,
    logger=None,
    progress_callback=None,
):
    _notificar(progress_callback, "Retornando da SP02...", 99)

    for tecla in (12, 3, 3):
        if not _esta_na_sp02(session):
            break

        try:
            session.findById("wnd[0]").sendVKey(tecla)
            wait_until_ready(session)
        except Exception:
            continue

        if _aguardar_saida_sp02(session, timeout=1.2):
            break

    if logger:
        logger.add(6, "Retorno da SP02 executado.", publico=True)


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

    _notificar(progress_callback, f"Reabrindo F110 no {identificacao}...", 99)

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
        logger.add(6, f"F110 reaberta no {identificacao}.", publico=True)

    _notificar(progress_callback, f"F110 reaberta no {identificacao}.", 99)

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
    _notificar(progress_callback, "Abrindo meio de pagamento...", 99)

    try:
        wait_for_element(session, "wnd[0]", timeout=10).maximize()
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

        wait_for_element(session, "wnd[1]", timeout=10).sendVKey(4)
        wait_until_ready(session)

        wait_for_element(session, "wnd[1]/tbar[0]/btn[0]", timeout=10).press()
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

    _notificar(progress_callback, "Meio de pagamento concluído.", 100)

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
    resultado = {}

    resultado.update(
        abrir_ordens_spool_boleto(
            session,
            logger=logger,
            progress_callback=progress_callback,
        )
    )

    _notificar(progress_callback, "Identificando par nota/boleto...", 97)
    linha_nota, linha_boleto = _localizar_par_spool_sp02(session)

    if logger:
        logger.add(
            6,
            "Par de spools localizado: "
            f"nota {linha_nota.get('spool') or 'sem número'} / "
            f"boleto {linha_boleto.get('spool') or 'sem número'}.",
            publico=True,
        )

    _notificar(progress_callback, "Validando spool da nota...", 98)
    dados_nota = _validar_detalhes_spool(session, linha_nota, logger=logger)
    resultado.update(_prefixar_dados_spool("nota", dados_nota))

    _notificar(progress_callback, "Validando spool do boleto...", 98)
    dados_boleto = _validar_detalhes_spool(session, linha_boleto, logger=logger)
    resultado.update(dados_boleto)
    resultado.update(_prefixar_dados_spool("boleto", dados_boleto))

    _focar_linha_spool(session, linha_boleto)

    nome_pdf_sugerido = montar_nome_pdf_sugerido(
        numero_boleto,
        dados=dados,
        cliente=cliente,
    )
    resultado["nome_pdf_sugerido"] = nome_pdf_sugerido

    if not _copiar_nome_pdf(nome_pdf_sugerido):
        raise RuntimeError("Não foi possível copiar o nome sugerido do PDF.")

    if logger:
        logger.add(
            6,
            "Nome do PDF copiado. Cole no PDFCreator.",
            publico=True,
        )

    _notificar(
        progress_callback,
        "Nome do PDF copiado. Imprimindo boleto...",
        98,
    )

    _imprimir_spool_selecionada(session)
    resultado["pdf_boleto"] = "IMPRESSAO_DISPARADA"
    resultado["spool_boleto"] = "IMPRESSAO_DISPARADA"

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
