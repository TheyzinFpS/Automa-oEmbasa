import re

from backend.flows.common import (
    aguardar_status_mudar,
    ler_propriedade,
    ler_status,
    notificar_progresso,
    resultado_padrao,
)
from backend.utils.sap_waits import element_exists, wait_for_element, wait_until_ready


_STATUS_BAR = "wnd[0]/sbar"
_CAMPO_DOCUMENTO_FATURAMENTO = "wnd[0]/usr/ctxtVBRK-VBELN"


# Extrai o número do documento de faturamento de mensagens do SAP.
def _extrair_numero_faturamento(texto):
    numeros = re.findall(r"\b\d{6,12}\b", str(texto or ""))
    if not numeros:
        return None
    return numeros[-1]


# Tenta capturar o faturamento diretamente do campo da VF01.
def _capturar_faturamento_por_campo(session):
    if not element_exists(session, _CAMPO_DOCUMENTO_FATURAMENTO):
        return None

    try:
        campo = session.findById(_CAMPO_DOCUMENTO_FATURAMENTO)
        valor = ler_propriedade(campo, "Text", "text").strip()
    except Exception:
        return None

    return _extrair_numero_faturamento(valor)


# Abre detalhe da mensagem de status para investigar retorno do SAP.
def _abrir_detalhe_status(session):
    try:
        session.findById(_STATUS_BAR).doubleClick()
        wait_until_ready(session)
        return True
    except Exception:
        return False


# Varre componentes SAP e coleta textos visiveis para diagnostico.
def _coletar_textos_recursivo(componente, textos, profundidade=0, max_profundidade=6):
    if profundidade > max_profundidade or componente is None:
        return

    for attr in ("Text", "text", "Title", "title", "Tooltip", "tooltip"):
        try:
            valor = getattr(componente, attr)
        except Exception:
            continue

        if valor:
            valor_limpo = str(valor).strip()
            if valor_limpo:
                textos.append(valor_limpo)

    try:
        filhos = getattr(componente, "Children", None)
        total = filhos.Count if filhos is not None else 0
    except Exception:
        total = 0

    for i in range(total):
        try:
            filho = filhos(i)
        except Exception:
            continue
        _coletar_textos_recursivo(
            filho,
            textos,
            profundidade + 1,
            max_profundidade=max_profundidade,
        )


# Le a janela de detalhe/status para descobrir mensagens contabeis.
def _ler_mensagem_detalhada(session):
    textos = []

    for alvo in ("wnd[1]", "wnd[0]"):
        try:
            componente = session.findById(alvo)
        except Exception:
            continue

        _coletar_textos_recursivo(componente, textos)

        if textos:
            break

    vistos = set()
    textos_unicos = []
    for t in textos:
        chave = t.strip()
        if not chave:
            continue
        if chave.lower() in vistos:
            continue
        vistos.add(chave.lower())
        textos_unicos.append(chave)

    return "\n".join(textos_unicos).strip()


# Detecta o caso em que a VF01 gerou faturamento, mas não gerou contábil.
def _mensagem_indica_erro_contabil(texto):
    texto_normalizado = str(texto or "").lower()

    erros_conhecidos = (
        "não gerou documento contábil",
        "nao gerou documento contabil",
        "não gerou doc. contábil",
        "nao gerou doc. contabil",
        "não gerou doc contábil",
        "nao gerou doc contabil",
        "não gerou documento contabil",
        "nao gerou documento contábil",
    )

    if any(frase in texto_normalizado for frase in erros_conhecidos):
        return True

    if ("não gerou" in texto_normalizado or "nao gerou" in texto_normalizado) and (
        "contábil" in texto_normalizado or "contabil" in texto_normalizado
    ):
        return True

    return False


# Fecha janela de detalhe/status tentando os caminhos mais comuns.
def _fechar_janela_detalhe(session):
    try:
        session.findById("wnd[0]/shellcont").close()
        wait_until_ready(session)
        return True
    except Exception:
        pass

    for alvo in (
        "wnd[1]/tbar[0]/btn[12]",
        "wnd[1]/tbar[0]/btn[0]",
    ):
        try:
            session.findById(alvo).press()
            wait_until_ready(session)
            return True
        except Exception:
            continue

    try:
        session.findById("wnd[0]/tbar[0]/btn[12]").press()
        wait_until_ready(session)
        return True
    except Exception:
        return False


# Retorna para a tela inicial depois da VF01.
def _retornar_tela_inicial(session):
    for _ in range(2):
        try:
            session.findById("wnd[0]/tbar[0]/btn[12]").press()
            wait_until_ready(session)
        except Exception:
            break


# Executa VF01, salva o documento e captura doc_fat/faturamento.
def criar_doc_faturamento(session, logger, progress_callback=None):
    progresso_atual = 8

    try:
        logger.add(2, "Criando documento de faturamento na VF01...", publico=True)

        notificar_progresso(
            progress_callback,
            "VF01",
            "processando",
            "Abrindo transação VF01...",
            progresso_atual,
        )
        session.findById("wnd[0]/tbar[0]/okcd").text = "/nVF01"
        session.findById("wnd[0]").sendVKey(0)

        wait_for_element(session, "wnd[0]/usr")
        wait_until_ready(session)

        progresso_atual = 82
        notificar_progresso(
            progress_callback,
            "VF01",
            "processando",
            "Salvando documento de faturamento...",
            progresso_atual,
        )
        status_antes, _ = ler_status(session, status_bar_id=_STATUS_BAR)
        session.findById("wnd[0]/tbar[0]/btn[11]").press()

        status_depois, tipo_status = aguardar_status_mudar(
            session,
            status_antes,
            timeout=10,
            status_bar_id=_STATUS_BAR,
        )
        faturamento = _extrair_numero_faturamento(status_depois)

        if not faturamento:
            faturamento = _capturar_faturamento_por_campo(session)

        if tipo_status in {"E", "A"} and not faturamento:
            raise Exception(
                f"SAP retornou erro ao salvar na VF01: {status_depois or 'sem mensagem'}"
            )

        if not faturamento:
            raise Exception(
                "A VF01 executou, mas não foi possível identificar o número do documento de faturamento. "
                f"Retorno SAP: {status_depois or 'sem mensagem'}"
            )

        logger.add(2, f"Retorno SAP VF01: {status_depois}")
        logger.add(2, f"Documento de faturamento criado: {faturamento}", publico=True)

        progresso_atual = 90
        notificar_progresso(
            progress_callback,
            "VF01",
            "processando",
            "Validando detalhes do faturamento...",
            progresso_atual,
        )

        mensagem_detalhada = ""
        if _abrir_detalhe_status(session):
            mensagem_detalhada = _ler_mensagem_detalhada(session)
            logger.add(2, f"Texto detalhado lido na VF01: {mensagem_detalhada}")

            if _mensagem_indica_erro_contabil(mensagem_detalhada):
                _fechar_janela_detalhe(session)
                _retornar_tela_inicial(session)

                mensagem_usuario = (
                    "Documento de faturamento gerado com indicativo de erro contábil. "
                    "Verifique manualmente antes de prosseguir."
                )

                logger.add(2, mensagem_usuario, publico=True)
                notificar_progresso(
                    progress_callback,
                    "VF01",
                    "erro",
                    mensagem_usuario,
                    progresso_atual,
                )

                return resultado_padrao(
                    ok=False,
                    etapa="VF01",
                    mensagem=mensagem_usuario,
                    dados={
                        "faturamento": faturamento,
                        "status_sap": status_depois,
                        "detalhe_status": mensagem_detalhada,
                    },
                    erro_tecnico=mensagem_detalhada,
                )

            _fechar_janela_detalhe(session)

        progresso_atual = 97
        notificar_progresso(
            progress_callback,
            "VF01",
            "processando",
            "Retornando para a tela inicial...",
            progresso_atual,
        )
        _retornar_tela_inicial(session)

        notificar_progresso(
            progress_callback,
            "VF01",
            "concluido",
            "Faturamento criado com sucesso.",
            100,
        )

        return resultado_padrao(
            ok=True,
            etapa="VF01",
            mensagem="Documento de faturamento criado com sucesso.",
            dados={
                "faturamento": faturamento,
                "doc_fat": faturamento,
                "status_sap": status_depois,
                "detalhe_status": mensagem_detalhada,
            },
        )

    except Exception as e:
        logger.add(2, f"Erro VF01: {e}", nivel="ERRO")
        notificar_progresso(
            progress_callback,
            "VF01",
            "erro",
            "Falha ao criar faturamento na VF01.",
            progresso_atual,
        )

        try:
            _fechar_janela_detalhe(session)
        except Exception:
            pass

        try:
            _retornar_tela_inicial(session)
        except Exception:
            pass

        return resultado_padrao(
            ok=False,
            etapa="VF01",
            mensagem="Erro ao criar documento de faturamento na VF01.",
            erro_tecnico=str(e),
        )
