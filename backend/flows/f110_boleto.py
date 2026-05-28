import json
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
_PDF_NOTICE_PREFIX = "PDF_NAME_READY::"
_PAYMENT_NOTICE_PREFIX = "PAYMENT_FILE_READY::"
_PDF_COPY_WAIT_SECONDS = 7


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



def _normalizar_numero_spool(valor):
    texto = str(valor or "").strip()
    texto = "".join(ch for ch in texto if ch.isdigit())
    return str(int(texto)) if texto else ""


def _limpar_parte_nome_arquivo(valor, fallback="INFORMAR"):
    texto = str(valor or "").strip() or fallback
    texto = re.sub(r'[<>:"/\\|?*]+', "-", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" .-") or fallback



def _buscar_valor_aninhado(objeto, caminhos):
    for caminho in caminhos:
        atual = objeto
        ok = True

        for chave in caminho:
            if isinstance(atual, dict):
                atual = atual.get(chave)
            else:
                atual = None

            if atual in (None, ""):
                ok = False
                break

        if ok:
            texto = str(atual).strip()
            if texto:
                return texto

    return ""


def _parece_nome_cliente_valido(valor):
    texto = _normalizar_texto(valor)

    if not texto:
        return False

    bloqueios = (
        "FILA AUTOMATICA",
        "PROCESSAMENTO SINCRONO",
        "SPOOL",
        "BOLETO",
        "CONTAS A RECEBER",
        "SAP",
        "PDFCREATOR",
        "VIABILIDADE",
        "PROJETO AGUA",
        "PROJETO ESGOTO",
    )

    return not any(item in texto for item in bloqueios)



def montar_nome_pdf_sugerido(numero_boleto, dados=None, cliente=None):
    dados = dados or {}
    endereco = dados.get("endereco") or {}
    tipo = str(dados.get("tipo") or "").strip().lower()

    # O nome pode vir de lugares diferentes conforme o fluxo:
    # boleto direto, cliente recém-criado, cliente em cache, cadastro, dados_cliente etc.
    # Evita usar textos operacionais do SAP como "Fila automática processamento síncrono".
    candidatos_nome = [
        dados.get("nome_cliente"),
        dados.get("cliente_nome"),
        dados.get("razao_social"),
        dados.get("razaoSocial"),
        dados.get("nome"),
        dados.get("nome1"),
        dados.get("nome_1"),
        _buscar_valor_aninhado(dados, [
            ("cliente", "nome"),
            ("cliente", "nome_cliente"),
            ("cliente", "razao_social"),
            ("cliente", "razaoSocial"),
            ("cliente", "nome1"),
            ("cliente_info", "nome"),
            ("cliente_info", "razao_social"),
            ("dados_cliente", "nome"),
            ("dados_cliente", "razao_social"),
            ("cadastro", "nome"),
            ("cadastro", "razao_social"),
            ("doc_info", "nome"),
            ("doc_info", "razao_social"),
        ]),
    ]

    nome_cliente = ""
    for candidato in candidatos_nome:
        if _parece_nome_cliente_valido(candidato):
            nome_cliente = str(candidato).strip()
            break

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


def montar_nome_arquivo_meio_pagamento(doc_fat, data=None):
    data_base = data or time.strftime("%Y.%m.%d")
    doc = _limpar_parte_nome_arquivo(doc_fat, "DOC_FAT")
    return f"{data_base} - {doc}"


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


def _aguardar_copia_interface(
    tipo,
    nome,
    notice_callback=None,
    progress_callback=None,
    mensagem=None,
    percentual=99,
    emitir_aviso=True,
    aguardar_confirmacao=True,
):
    """
    Copia o nome e emite aviso apenas informativo.

    Importante:
    - não chama notice_callback;
    - não espera confirmação do frontend;
    - não bloqueia o backend;
    - o botão do modal apenas copia/fecha localmente no app.js.
    """

    _copiar_nome_pdf(nome)

    if not emitir_aviso:
        return True

    prefixo = _PAYMENT_NOTICE_PREFIX if tipo == "payment" else _PDF_NOTICE_PREFIX

    _notificar(
        progress_callback,
        f"{prefixo}{nome}",
        percentual,
        status="concluido" if tipo == "pdf" else "processando",
    )

    return True


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


def _limpar_selecao_sp02_com_shift_f6(session, logger=None):
    """
    Limpa a seleção da SP02 com SHIFT + F6 antes de ir para a linha do boleto.
    No SAP GUI Scripting, sendVKey(30) corresponde ao SHIFT + F6.
    """

    try:
        session.findById("wnd[0]").sendVKey(30)
        wait_until_ready(session)
        time.sleep(0.4)

        if logger:
            logger.add(
                6,
                "Seleção da SP02 limpa com SHIFT+F6.",
                publico=False,
            )

        return True

    except Exception as exc:
        if logger:
            logger.add(
                6,
                f"Falha ao limpar seleção da SP02 com SHIFT+F6: {exc}",
                nivel="AVISO",
                publico=False,
            )

        return False


def _localizar_primeiro_boleto_sp02(session):
    """
    Localiza diretamente o primeiro BOLETO (CONTAS A RECEBER) em ordem decrescente.
    A nota de acompanhamento não é mais validada nem acessada.
    """

    linhas = _coletar_linhas_sp02(session)
    boletos = _ordenar_linhas_sp02_decrescente(
        [linha for linha in linhas if _linha_e_boleto(linha)]
    )

    if not boletos:
        resumo = "; ".join(
            linha.get("texto", "")
            for linha in linhas[:8]
            if linha.get("texto")
        )
        raise RuntimeError(
            "Nenhuma spool BOLETO (CONTAS A RECEBER) foi encontrada na SP02. "
            f"Primeiras linhas lidas: {resumo or 'nenhuma'}."
        )

    boleto = boletos[0]
    linha_y = int(boleto.get("linha"))

    # Força os IDs reais da linha do boleto encontrada.
    boleto["linha"] = linha_y
    boleto["titulo_id"] = f"wnd[0]/usr/lbl[51,{linha_y}]"
    boleto["checkbox_id"] = f"wnd[0]/usr/chk[1,{linha_y}]"

    return boleto


def _relocalizar_boleto_apos_nota(session, linha_nota_original, logger=None):
    """
    Depois de validar a nota e voltar com F12, limpa a seleção com SHIFT+F6
    e força a próxima linha visual da SP02 como boleto.

    Regra validada no SAP:
    Nota   -> lbl[51,Y]
    Boleto -> lbl[51,Y+1]
    """

    _limpar_selecao_sp02_com_shift_f6(session, logger=logger)

    linha_nota_y = int(linha_nota_original.get("linha"))
    linha_boleto_y = linha_nota_y + 1

    linhas = _coletar_linhas_sp02(session)
    por_linha = {int(linha["linha"]): linha for linha in linhas}
    linha_boleto = por_linha.get(linha_boleto_y)

    if not linha_boleto:
        linha_boleto = {
            "linha": linha_boleto_y,
            "spool": "",
            "data": "",
            "hora": "",
            "status": "",
            "paginas": "",
            "titulo": "BOLETO (CONTAS A RECEBER)",
            "titulo_id": f"wnd[0]/usr/lbl[51,{linha_boleto_y}]",
            "checkbox_id": f"wnd[0]/usr/chk[1,{linha_boleto_y}]",
            "texto": "BOLETO (CONTAS A RECEBER)",
            "texto_normalizado": "BOLETO (CONTAS A RECEBER)",
        }

    linha_boleto["linha"] = linha_boleto_y
    linha_boleto["titulo_id"] = f"wnd[0]/usr/lbl[51,{linha_boleto_y}]"
    linha_boleto["checkbox_id"] = f"wnd[0]/usr/chk[1,{linha_boleto_y}]"

    return linha_boleto


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


def _selecionar_linha_por_y(session, y_linha, caret_position=13):
    """
    Seleciona/foca a linha visual da SP02 pelo mesmo princípio usado na nota:
    foco no label da coluna 51 e depois F2.

    A limpeza de seleção deve ocorrer antes com SHIFT+F6.
    """

    y_linha = int(y_linha)
    label_id = f"wnd[0]/usr/lbl[51,{y_linha}]"

    label = session.findById(label_id)

    try:
        label.setFocus()
    except Exception:
        try:
            label.SetFocus()
        except Exception:
            pass

    try:
        label.caretPosition = int(caret_position)
    except Exception:
        pass

    wait_until_ready(session)
    time.sleep(0.3)

    return True


def _focar_linha_spool_por_modo(session, linha, modo):
    linha_y = linha.get("linha")

    if modo == "selecionar_y" and linha_y is not None:
        return _selecionar_linha_por_y(
            session,
            int(linha_y),
            caret_position=13,
        )

    if modo == "coluna_51" and linha_y is not None:
        return _focar_elemento(
            session,
            f"wnd[0]/usr/lbl[51,{int(linha_y)}]",
            caret_position=13,
        )

    if modo == "titulo":
        titulo_id = linha.get("titulo_id")
        if titulo_id:
            return _focar_elemento(session, titulo_id, caret_position=2)

    if modo == "checkbox":
        checkbox_id = linha.get("checkbox_id")
        if checkbox_id:
            try:
                checkbox = session.findById(checkbox_id)
                checkbox.setFocus()
            except Exception:
                try:
                    checkbox = session.findById(checkbox_id)
                    checkbox.SetFocus()
                except Exception:
                    pass

            return True

    return False


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


def _validar_conteudo_detalhe_spool(session, linha, logger=None):
    textos = _coletar_textos_tela(session)
    numero_detalhe = ""

    try:
        numero_detalhe = _texto_elemento(
            session.findById("wnd[0]/usr/txtTSP01_SP0R-RQID_CHAR")
        )
    except Exception:
        pass

    if linha.get("spool"):
        spool_lista = _normalizar_numero_spool(linha.get("spool"))
        spool_detalhe = _normalizar_numero_spool(numero_detalhe)

        if spool_lista and spool_detalhe and spool_lista != spool_detalhe:
            raise RuntimeError(
                "Detalhe da spool divergente: "
                f"lista={linha['spool']} detalhe={numero_detalhe}."
            )

        if not spool_detalhe and not _tela_contem(textos, linha["spool"]):
            raise RuntimeError(
                f"Detalhe da spool não confirmou o número {linha['spool']}."
            )

    for campo in ("titulo", "data", "hora"):
        valor = linha.get(campo)
        if valor and not _tela_contem(textos, valor):
            raise RuntimeError(f"Detalhe da spool não confirmou {campo}: {valor}.")

    encerrado = _checkbox_encerrado_marcado(session)
    # A checkbox "Encerrado, já não é possível anexar" é apenas informativa
    # neste fluxo e não deve bloquear a impressão do boleto.

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


def _voltar_para_lista_sp02(session):
    try:
        session.findById("wnd[0]").sendVKey(12)
        wait_until_ready(session)
    except Exception:
        pass


def _validar_detalhes_spool(session, linha, logger=None, voltar_apos_validar=False):
    """
    Entra UMA única vez no detalhe do boleto, valida os dados visíveis
    e permanece nessa tela para disparar a impressão.

    Importante:
    - Não volta para a lista da SP02 após validar.
    - Não tenta outros modos/fallbacks se algo falhar.
    - Não entra novamente na spool.
    """

    try:
        # Prioridade: usa o ID real do título lido na SP02.
        titulo_id = linha.get("titulo_id")
        linha_y = linha.get("linha")

        if titulo_id:
            _focar_elemento(session, titulo_id, caret_position=13)
        elif linha_y is not None:
            _focar_elemento(
                session,
                f"wnd[0]/usr/lbl[51,{int(linha_y)}]",
                caret_position=13,
            )
        else:
            raise RuntimeError("Linha do boleto sem título_id e sem coordenada Y.")

        session.findById("wnd[0]").sendVKey(2)
        wait_until_ready(session)

        dados = _validar_conteudo_detalhe_spool(session, linha, logger=logger)

        if logger:
            logger.add(
                6,
                "Detalhe do boleto aberto e validado uma única vez. "
                "Permanecendo na tela do boleto para impressão.",
                publico=True,
            )

        return dados

    except Exception as exc:
        raise RuntimeError(
            f"Erro ao entrar/validar a spool do boleto uma única vez: {exc}"
        ) from exc


def _voltar_lista_e_selecionar_checkbox_boleto(session, linha_boleto, logger=None):
    """
    Depois de validar o detalhe do boleto, volta com F12 para a lista da SP02,
    marca a checkbox da mesma linha do boleto e deixa a linha em foco para impressão.
    """

    y_linha = int(linha_boleto.get("linha"))
    checkbox_id = f"wnd[0]/usr/chk[1,{y_linha}]"
    label_id = f"wnd[0]/usr/lbl[51,{y_linha}]"

    try:
        session.findById("wnd[0]").sendVKey(12)
        wait_until_ready(session, timeout=8)
        time.sleep(0.5)
    except Exception as exc:
        raise RuntimeError(f"Erro ao voltar do detalhe do boleto para a lista SP02: {exc}") from exc

    try:
        checkbox = wait_for_element(session, checkbox_id, timeout=10)
        checkbox.selected = True

        try:
            checkbox.setFocus()
        except Exception:
            try:
                checkbox.SetFocus()
            except Exception:
                pass

        # Reforça foco no título da mesma linha, sem perder a seleção da checkbox.
        try:
            label = session.findById(label_id)
            label.setFocus()
            label.caretPosition = 13
        except Exception:
            pass

        wait_until_ready(session, timeout=5)
        time.sleep(0.3)

        if logger:
            logger.add(
                6,
                f"Checkbox da spool do boleto selecionada na linha Y={y_linha}.",
                publico=True,
            )

        return True

    except Exception as exc:
        raise RuntimeError(
            f"Erro ao selecionar checkbox da spool do boleto em {checkbox_id}: {exc}"
        ) from exc


def _abrir_validar_voltar_e_marcar_boleto(session, linha_boleto, logger=None):
    """
    Fluxo equivalente ao VBS validado pelo usuário:

    session.findById("wnd[0]").maximize
    session.findById("wnd[0]/usr/chk[1,Y]").selected = false
    session.findById("wnd[0]/usr/lbl[51,Y]").setFocus
    session.findById("wnd[0]/usr/lbl[51,Y]").caretPosition = 5
    session.findById("wnd[0]").sendVKey 2
    session.findById("wnd[0]").sendVKey 12
    session.findById("wnd[0]/usr/chk[1,Y]").selected = true
    session.findById("wnd[0]/usr/chk[1,Y]").setFocus
    """

    y_linha = int(linha_boleto.get("linha"))
    chk_id = f"wnd[0]/usr/chk[1,{y_linha}]"
    lbl_id = f"wnd[0]/usr/lbl[51,{y_linha}]"

    wait_for_element(session, "wnd[0]", timeout=10).maximize()
    wait_until_ready(session)

    checkbox = wait_for_element(session, chk_id, timeout=10)
    checkbox.selected = False

    label = wait_for_element(session, lbl_id, timeout=10)
    label.setFocus()
    label.caretPosition = 5

    session.findById("wnd[0]").sendVKey(2)
    wait_until_ready(session)

    dados_boleto = _validar_conteudo_detalhe_spool(
        session,
        linha_boleto,
        logger=logger,
    )

    session.findById("wnd[0]").sendVKey(12)
    wait_until_ready(session)

    checkbox = wait_for_element(session, chk_id, timeout=10)
    checkbox.selected = True
    checkbox.setFocus()

    wait_until_ready(session)
    time.sleep(0.3)

    if logger:
        logger.add(
            6,
            f"Boleto validado e checkbox marcada na SP02 na linha Y={y_linha}.",
            publico=True,
        )

    return dados_boleto


def _marcar_boleto_sp02_sem_validar(
    session,
    linha_boleto,
    selecionado=True,
    logger=None,
):
    """
    Marca ou desmarca diretamente a linha visual do boleto na SP02.
    Usado no fluxo Água + Esgoto, onde a ordem decrescente da SP02 define
    Esgoto primeiro e Água em seguida, sem abrir o detalhe da spool.
    """

    y_linha = int(linha_boleto.get("linha"))
    chk_id = f"wnd[0]/usr/chk[1,{y_linha}]"
    lbl_id = f"wnd[0]/usr/lbl[51,{y_linha}]"
    selecionado = bool(selecionado)

    wait_for_element(session, "wnd[0]", timeout=10).maximize()
    wait_until_ready(session)

    checkbox = wait_for_element(session, chk_id, timeout=10)
    checkbox.selected = selecionado

    try:
        checkbox.setFocus()
    except Exception:
        try:
            checkbox.SetFocus()
        except Exception:
            pass

    try:
        label = session.findById(lbl_id)
        label.setFocus()
        label.caretPosition = 5
    except Exception:
        pass

    wait_until_ready(session)
    time.sleep(0.3)

    if logger:
        acao = "marcada" if selecionado else "desmarcada"
        logger.add(
            6,
            f"Linha de boleto {acao} diretamente na SP02 em Y={y_linha}.",
            publico=True,
        )

    return {
        "linha": y_linha,
        "spool": linha_boleto.get("spool"),
        "titulo": linha_boleto.get("titulo"),
        "data": linha_boleto.get("data"),
        "hora": linha_boleto.get("hora"),
        "status": linha_boleto.get("status"),
        "paginas": linha_boleto.get("paginas"),
    }


def _imprimir_spool_selecionada(session):
    """
    Dispara a impressão/exportação da spool pela opção de menu informada pelo VBS:

        session.findById("wnd[0]/mbar/menu[0]/menu[0]/menu[0]").select()

    Esta função não aguarda confirmação do usuário e não tenta confirmar popup.
    Após o comando, o fluxo segue direto para F110 e Meio de pagamento.
    """

    try:
        wait_for_element(session, "wnd[0]", timeout=10).maximize()
        wait_until_ready(session)

        wait_for_element(
            session,
            "wnd[0]/mbar/menu[0]/menu[0]/menu[0]",
            timeout=10,
        ).select()

        wait_until_ready(session, timeout=12)
        time.sleep(0.8)

    except Exception as exc:
        raise RuntimeError(
            f"Erro ao acionar impressão/exportação da spool pelo menu: {exc}"
        ) from exc

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


def _aguardar_salvamento_meio_pagamento(
    session,
    logger=None,
    progress_callback=None,
    intervalo=1,
    aviso_intervalo=300,
):
    inicio = time.monotonic()
    proximo_aviso = inicio + aviso_intervalo

    if logger:
        logger.add(
            6,
            "Aguardando o usuário concluir o salvamento do meio de pagamento no Explorer.",
            publico=True,
        )

    _notificar(
        progress_callback,
        "Janela de salvamento aberta. Salve o arquivo para continuar.",
        99,
    )

    while True:
        try:
            return session.findById("wnd[1]/tbar[0]/btn[0]")
        except Exception:
            agora = time.monotonic()

            if agora >= proximo_aviso:
                minutos = max(1, int((agora - inicio) // 60))
                _notificar(
                    progress_callback,
                    f"Aguardando salvamento do meio de pagamento ha {minutos} min.",
                    99,
                )
                proximo_aviso = agora + aviso_intervalo

            time.sleep(max(0.2, float(intervalo or 1)))


def baixar_arquivo_meio_pagamento(
    session,
    logger=None,
    progress_callback=None,
    notice_callback=None,
    data_exec=None,
    identificacao=None,
    cliente=None,
    doc_fat=None,
):
    """
    Fluxo simples/padrão do meio de pagamento.

    Regras:
    - Não abre modal.
    - Não copia nome automaticamente.
    - Não controla Explorer pelo Python.
    - Apenas abre o F4, aguarda o usuário selecionar/salvar o arquivo,
      confirma o botão do SAP e segue para SP02.
    """

    nome_arquivo = montar_nome_arquivo_meio_pagamento(doc_fat)
    payload_nome = json.dumps(
        {
            "nome": nome_arquivo,
            "cliente": cliente,
            "doc_fat": doc_fat,
        },
        ensure_ascii=False,
    )

    _notificar(progress_callback, f"{_PAYMENT_NOTICE_PREFIX}{payload_nome}", 98)
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

        # ORDEM OBRIGATÓRIA:
        # O F4 precisa vir imediatamente após o sendVKey(18).
        # Não inserir modal, callback, cópia, sleep ou lógica de Explorer entre eles.
        session.findById("wnd[0]").sendVKey(18)
        session.findById("wnd[1]").sendVKey(4)
        wait_until_ready(session)

        _notificar(
            progress_callback,
            "Janela de salvamento aberta. Selecione/salve o arquivo para continuar.",
            99,
        )

        # Aguarda o usuário concluir a seleção/salvamento no Explorer.
        # Quando o SAP voltar com o botão OK disponível, pressiona e segue.
        _aguardar_salvamento_meio_pagamento(
            session,
            logger=logger,
            progress_callback=progress_callback,
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

    _notificar(progress_callback, "Meio de pagamento concluído.", 100)

    return {
        "arquivo_meio_pagamento": "CONFIRMADO",
        "nome_arquivo_meio_pagamento": nome_arquivo,
    }


def finalizar_boleto_f110(
    session,
    logger=None,
    progress_callback=None,
    notice_callback=None,
    dados=None,
    cliente=None,
    numero_boleto=None,
    data_exec=None,
    identificacao=None,
    selecionar_boleto=True,
    retornar_apos_boleto=False,
    aguardar_apos_copia_segundos=0,
):
    resultado = {}

    resultado.update(
        baixar_arquivo_meio_pagamento(
            session,
            logger=logger,
            progress_callback=progress_callback,
            notice_callback=notice_callback,
            data_exec=data_exec,
            identificacao=identificacao,
            cliente=cliente,
            doc_fat=numero_boleto,
        )
    )

    if not selecionar_boleto:
        return resultado

    resultado.update(
        abrir_ordens_spool_boleto(
            session,
            logger=logger,
            progress_callback=progress_callback,
        )
    )

    _notificar(progress_callback, "Localizando boleto mais recente...", 97)
    linha_boleto = _localizar_primeiro_boleto_sp02(session)

    if logger:
        logger.add(
            6,
            "Spool de boleto localizada diretamente: "
            f"{linha_boleto.get('spool') or 'sem número'} - "
            f"{linha_boleto.get('titulo') or 'sem título'} "
            f"(linha Y={linha_boleto.get('linha')}).",
            publico=True,
        )

    _notificar(progress_callback, "Validando spool do boleto...", 98)
    dados_boleto = _abrir_validar_voltar_e_marcar_boleto(
        session,
        linha_boleto,
        logger=logger,
    )
    resultado.update(dados_boleto)
    resultado.update(_prefixar_dados_spool("boleto", dados_boleto))

    nome_pdf_sugerido = montar_nome_pdf_sugerido(
        numero_boleto,
        dados=dados,
        cliente=cliente,
    )
    resultado["nome_pdf_sugerido"] = nome_pdf_sugerido

    if logger:
        logger.add(
            6,
            "Linha de boleto selecionada na SP02. ImpressÃ£o manual liberada.",
            publico=True,
        )

    # O PDFCreator precisa ser acionado manualmente; comandos SAP que abrem
    # programa externo não são confiáveis neste ambiente.
    _notificar(
        progress_callback,
        "Linha de boleto selecionada. Aguardando cópia do nome do PDF...",
        100,
        status="concluido",
    )
    _aguardar_copia_interface(
        "pdf",
        nome_pdf_sugerido,
        notice_callback=None,
        progress_callback=progress_callback,
        mensagem="Nome do PDF copiado.",
        percentual=100,
        emitir_aviso=True,
        aguardar_confirmacao=False,
    )

    if aguardar_apos_copia_segundos:
        _notificar(
            progress_callback,
            f"Aguardando {aguardar_apos_copia_segundos} segundos após cópia do nome do PDF...",
            100,
            status="processando",
        )
        time.sleep(max(0, float(aguardar_apos_copia_segundos or 0)))

    if retornar_apos_boleto:
        voltar_tela_inicial_com_f3(
            session,
            logger=logger,
            progress_callback=progress_callback,
        )

    resultado["pdf_boleto"] = "LINHA_SELECIONADA"
    resultado["spool_boleto"] = "LINHA_SELECIONADA"
    resultado["impressao_manual"] = True

    _notificar(
        progress_callback,
        "Boleto gerado com sucesso. Linha selecionada e nome do PDF copiado.",
        100,
        status="concluido",
    )

    return resultado


def selecionar_boletos_sp02(
    session,
    boletos,
    logger=None,
    progress_callback=None,
    notice_callback=None,
    aguardar_apos_copia_segundos=_PDF_COPY_WAIT_SECONDS,
):
    boletos = list(boletos or [])

    if not boletos:
        raise RuntimeError("Nenhum boleto informado para selecionar na SP02.")

    resultado = {}

    resultado.update(
        abrir_ordens_spool_boleto(
            session,
            logger=logger,
            progress_callback=progress_callback,
        )
    )

    linhas = sorted(
        [linha for linha in _coletar_linhas_sp02(session) if _linha_e_boleto(linha)],
        key=lambda linha: int(linha.get("linha") or 0),
    )

    if len(linhas) < len(boletos):
        raise RuntimeError(
            "Quantidade insuficiente de spools de boleto na SP02. "
            f"Esperado {len(boletos)}, encontrado {len(linhas)}."
        )

    spools = []
    linha_anterior = -1

    for indice, boleto in enumerate(boletos):
        candidatos = [
            linha
            for linha in linhas
            if int(linha.get("linha") or 0) > linha_anterior
        ]

        if not candidatos:
            raise RuntimeError(
                "Não foi possível localizar a próxima linha de boleto na SP02."
            )

        linha = candidatos[0]
        linha_anterior = int(linha.get("linha") or 0)
        tipo_label = _TIPOS_LABEL.get(str(boleto.get("tipo") or ""), boleto.get("tipo"))

        if logger:
            logger.add(
                6,
                f"Selecionando spool de boleto de {tipo_label}: "
                f"{linha.get('spool') or 'sem número'} - "
                f"{linha.get('titulo') or 'sem título'} "
                f"(linha Y={linha.get('linha')}).",
                publico=True,
            )

        _notificar(
            progress_callback,
            f"Selecionando boleto de {tipo_label} na SP02...",
            98,
        )
        dados_boleto = _marcar_boleto_sp02_sem_validar(
            session,
            linha,
            selecionado=True,
            logger=logger,
        )
        nome_pdf = montar_nome_pdf_sugerido(
            boleto.get("doc_fat"),
            dados=boleto.get("dados"),
            cliente=boleto.get("cliente"),
        )
        spools.append(
            {
                "tipo": boleto.get("tipo"),
                "doc_fat": boleto.get("doc_fat"),
                "nome_pdf_sugerido": nome_pdf,
                **dados_boleto,
            }
        )

        _notificar(
            progress_callback,
            f"Boleto de {tipo_label} selecionado. Aguardando cópia do nome...",
            99,
        )
        _aguardar_copia_interface(
            "pdf",
            nome_pdf,
            notice_callback=notice_callback,
            progress_callback=progress_callback,
            mensagem=f"Copie o nome do PDF do projeto {tipo_label}.",
            percentual=100 if indice == len(boletos) - 1 else 99,
        )

        _notificar(
            progress_callback,
            f"Aguardando {aguardar_apos_copia_segundos} segundos após cópia do boleto de {tipo_label}...",
            99,
        )
        time.sleep(max(0, float(aguardar_apos_copia_segundos or 0)))

        if indice < len(boletos) - 1:
            _notificar(
                progress_callback,
                f"Desmarcando boleto de {tipo_label} para seguir ao próximo...",
                99,
            )
            _marcar_boleto_sp02_sem_validar(
                session,
                linha,
                selecionado=False,
                logger=logger,
            )

    fechar_popups_se_existirem(session)

    voltar_tela_inicial_com_f3(
        session,
        logger=logger,
        progress_callback=progress_callback,
    )

    fechar_popups_se_existirem(session)

    resultado.update(
        {
            "pdf_boleto": "LINHAS_SELECIONADAS",
            "spool_boleto": "LINHAS_SELECIONADAS",
            "impressao_manual": True,
            "spools_boletos": spools,
            "nomes_pdf_sugeridos": {
                str(spool.get("tipo") or ""): spool.get("nome_pdf_sugerido")
                for spool in spools
                if spool.get("nome_pdf_sugerido")
            },
        }
    )
    _notificar(
        progress_callback,
        "Boletos Água + Esgoto selecionados e nomes copiados.",
        100,
        status="concluido",
    )
    return resultado
