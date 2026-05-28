from backend.cache.cliente_cache import ClienteCache
from backend.flows.common import notificar_progresso, resultado_padrao
from backend.utils.sap_waits import (
    element_exists,
    press_and_wait,
    send_vkey_and_wait,
    wait_for_element,
    wait_until_ready,
)

cache_cliente = ClienteCache()

_TIPO_PARA_SETOR = {
    "viabilidade": "AE",
    "agua": "AG",
    "esgoto": "EG",
    "agua_esgoto": ("AG", "EG"),
}

_SETOR_PARA_TIPO = {
    "AE": "viabilidade",
    "AG": "agua",
    "EG": "esgoto",
}

_TIPO_LABEL = {
    "viabilidade": "Viabilidade",
    "agua": "Água",
    "esgoto": "Esgoto",
    "agua_esgoto": "Água + Esgoto",
}

_CAMPO_CNPJ = (
    "wnd[2]/usr/tabsG_SELONETABSTRIP/tabpTAB006/"
    "ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/"
    "txtG_SELFLD_TAB-LOW[0,24]"
)

_CAMPO_CPF = (
    "wnd[2]/usr/tabsG_SELONETABSTRIP/tabpTAB006/"
    "ssubSUBSCR_PRESEL:SAPLSDH4:0220/sub:SAPLSDH4:0220/"
    "txtG_SELFLD_TAB-LOW[1,24]"
)

_CAMPO_CLIENTE = "wnd[1]/usr/ctxtRF02D-KUNNR"
_BOTAO_AREAS_CLIENTE = "wnd[1]/usr/btnBUTTON2"
_TABELA_AREAS_CLIENTE = "wnd[2]/usr/tblSAPMF02DTCTRL_KUNDENVERTRIEB"
_BOTAO_CONFIRMAR_CLIENTE = "wnd[1]/tbar[0]/btn[0]"
_CAMPO_NOME1_CLIENTE = (
    "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
    "ssubSUBSC:SAPLATAB:0201/subAREA1:SAPMF02D:7111/"
    "subADDRESS:SAPLSZA1:0300/subCOUNTRY_SCREEN:SAPLSZA1:0301/"
    "txtADDR1_DATA-NAME1"
)
_CAMPO_NOME2_CLIENTE = (
    "wnd[0]/usr/subSUBTAB:SAPLATAB:0100/tabsTABSTRIP100/tabpTAB01/"
    "ssubSUBSC:SAPLATAB:0201/subAREA1:SAPMF02D:7111/"
    "subADDRESS:SAPLSZA1:0300/subCOUNTRY_SCREEN:SAPLSZA1:0301/"
    "txtADDR1_DATA-NAME2"
)


_TEXTOS_IGNORADOS_NOME_CLIENTE = {
    "imposto ret.na fonte",
    "seguros",
    "correspondencia",
    "correspondência",
    "pagamentos",
    "administracao conta",
    "administração conta",
    "dados da empresa",
    "cliente",
    "empresa",
    "emba",
    "embasa",
    "área de vendas",
    "area de vendas",
    "organização vendas",
    "organizacao vendas",
    "canal distribuição",
    "canal distribuicao",
    "setor de atividade",
    "todas as áreas vendas...",
    "todas as areas vendas...",
    "áreas de vendas do cliente...",
    "areas de vendas do cliente...",
    "projeto",
    "distr. água/ esgoto",
    "distr. agua/ esgoto",
    "água",
    "agua",
    "esgoto",
    "viabilidade",
}

_FRAGMENTOS_IGNORADOS_NOME_CLIENTE = (
    "cliente exibir",
    "exibir:",
    "1ª tela",
    "1a tela",
    "áreas de vendas",
    "areas de vendas",
    "organização vendas",
    "organizacao vendas",
    "canal distribuição",
    "canal distribuicao",
    "setor de atividade",
    "todas as",
)


def limpar_doc(doc):
    return "".join(filter(str.isdigit, str(doc)))


def tipo_documento(doc):
    if len(doc) == 11:
        return "cpf"
    if len(doc) == 14:
        return "cnpj"
    raise ValueError("Documento inválido")


def _normalizar_tipo_solicitacao(tipo):
    tipo_normalizado = str(tipo or "").strip().lower()

    if tipo_normalizado not in _TIPO_PARA_SETOR:
        raise ValueError(f"Tipo de solicitação inválido para XD03: {tipo}")

    return tipo_normalizado


def _ler_texto(componente):
    for atributo in ("Text", "text"):
        try:
            valor = getattr(componente, atributo)
        except Exception:
            continue

        if valor is not None:
            return str(valor).strip()

    return ""


def _montar_nome_cliente(nome1, nome2):
    partes = [
        str(nome1 or "").strip(),
        str(nome2 or "").strip(),
    ]

    return " ".join(parte for parte in partes if parte).strip()


def _coletar_textos_recursivo(componente, textos, profundidade=0, max_profundidade=5):
    if componente is None or profundidade > max_profundidade:
        return

    texto = _ler_texto(componente)
    if texto:
        textos.append(texto)

    try:
        filhos = getattr(componente, "Children", None)
        total = filhos.Count if filhos is not None else 0
    except Exception:
        total = 0

    for indice in range(total):
        try:
            filho = filhos(indice)
        except Exception:
            continue

        _coletar_textos_recursivo(
            filho,
            textos,
            profundidade=profundidade + 1,
            max_profundidade=max_profundidade,
        )


def _texto_parece_nome_cliente(texto, codigo_cliente, documento):
    valor = str(texto or "").strip()
    normalizado = valor.lower()
    somente_digitos = limpar_doc(valor)

    if len(valor) < 4:
        return False

    if not any(char.isalpha() for char in valor):
        return False

    if normalizado in _TEXTOS_IGNORADOS_NOME_CLIENTE:
        return False

    if any(fragmento in normalizado for fragmento in _FRAGMENTOS_IGNORADOS_NOME_CLIENTE):
        return False

    if str(codigo_cliente or "").strip() and str(codigo_cliente).strip() in valor:
        return False

    if documento and somente_digitos == documento:
        return False

    return True


def _capturar_nome_cliente(session, codigo_cliente, documento):
    # Tenta ler o nome exibido ao lado do cliente na XD03.
    # O SAP GUI pode variar o ID do campo de nome conforme layout/tema, então a
    # leitura é feita por varredura dos textos visíveis da janela de cliente.
    textos = []

    for alvo in ("wnd[1]", "wnd[0]"):
        try:
            componente = session.findById(alvo)
        except Exception:
            continue

        _coletar_textos_recursivo(componente, textos)

    candidatos = []
    vistos = set()

    for texto in textos:
        valor = str(texto or "").strip()
        chave = valor.lower()

        if chave in vistos:
            continue

        vistos.add(chave)

        if _texto_parece_nome_cliente(valor, codigo_cliente, documento):
            candidatos.append(valor)

    if not candidatos:
        return ""

    candidatos.sort(
        key=lambda item: (
            " " not in item,
            len(item) < 8,
            -len(item),
        )
    )
    return candidatos[0].strip()


def _fechar_popup_areas_cliente(session):
    # Fecha somente a janela de areas de vendas, preservando a tela inicial XD03.
    for element_id in (
        "wnd[2]/tbar[0]/btn[12]",
        "wnd[2]/usr/btnSPOP-OPTION2",
    ):
        try:
            session.findById(element_id).press()
            wait_until_ready(session)
            return
        except Exception:
            pass

    try:
        session.findById("wnd[2]").sendVKey(12)
        wait_until_ready(session)
    except Exception:
        pass


def _ir_para_dados_gerais_cliente(session, logger=None):
    """
    Fallback único para captura de nome na XD03.

    Se Nome 1/Nome 2 não forem encontrados, entende que o SAP caiu
    na tela de Dados da empresa ou em outra tela da XD03. Então executa
    CTRL + F1 por sendVKey(25) para retornar aos Dados gerais e refaz
    a leitura padrão de DATA-NAME1 e DATA-NAME2.
    """

    try:
        session.findById("wnd[0]").maximize()
    except Exception:
        pass

    try:
        session.findById("wnd[0]").sendVKey(25)
        wait_until_ready(session)
    except Exception as exc:
        if logger:
            logger.add(
                0,
                f"Falha ao executar CTRL+F1 para Dados gerais: {exc}",
                nivel="DEBUG",
                publico=False,
            )

    try:
        session.findById("wnd[0]/shellcont").close()
        wait_until_ready(session)
    except Exception:
        pass

    if logger:
        logger.add(
            0,
            "Fallback XD03 executado: CTRL+F1 para retornar aos Dados gerais.",
            nivel="DEBUG",
            publico=False,
        )


def _ler_nome_cliente_dados_gerais(session):
    # Leitura oficial da aba Endereco: Nome 1 + Nome 2.
    nome1 = _ler_texto(wait_for_element(session, _CAMPO_NOME1_CLIENTE, timeout=8))
    nome2 = ""

    try:
        nome2 = _ler_texto(session.findById(_CAMPO_NOME2_CLIENTE))
    except Exception:
        nome2 = ""

    return _montar_nome_cliente(nome1, nome2)


def _voltar_da_tela_dados_gerais_cliente(session, logger):
    # Depois de ler Nome 1/Nome 2, volta para a tela anterior da XD03.
    # A VA01 abre por /nVA01, mas este retorno evita deixar a XD03 presa em aba interna.
    if not element_exists(session, _CAMPO_NOME1_CLIENTE):
        return

    for _ in range(2):
        try:
            session.findById("wnd[0]").sendVKey(12)
            wait_until_ready(session)
        except Exception:
            break

        if not element_exists(session, _CAMPO_NOME1_CLIENTE):
            break

    logger.add(
        0,
        "Retorno da tela de dados gerais do cliente concluido.",
        nivel="DEBUG",
        publico=False,
    )


def _capturar_nome_cliente_dados_gerais(
    session,
    codigo_cliente,
    documento,
    logger,
    progress_callback=None,
):
    # 1. Tenta Nome 1 / Nome 2 normalmente.
    # 2. Se não encontrar, executa CTRL+F1 para Dados gerais.
    # 3. Tenta Nome 1 / Nome 2 novamente.
    notificar_progresso(
        progress_callback,
        "XD03",
        "processando",
        "Capturando nome do cliente...",
        97,
    )

    try:
        _fechar_popup_areas_cliente(session)

        if not element_exists(session, _CAMPO_NOME1_CLIENTE):
            press_and_wait(session, _BOTAO_CONFIRMAR_CLIENTE)

        nome_cliente = _ler_nome_cliente_dados_gerais(session)

        if nome_cliente:
            logger.add(0, f"Nome do cliente identificado: {nome_cliente}")
            return nome_cliente

        _ir_para_dados_gerais_cliente(session, logger=logger)
        nome_cliente = _ler_nome_cliente_dados_gerais(session)

        if nome_cliente:
            logger.add(
                0,
                f"Nome do cliente identificado após fallback CTRL+F1: {nome_cliente}",
            )
            return nome_cliente

    except Exception as exc:
        logger.add(
            0,
            f"Nao foi possivel ler Nome 1/Nome 2 da XD03: {exc}",
            nivel="DEBUG",
            publico=False,
        )
    finally:
        _voltar_da_tela_dados_gerais_cliente(session, logger)

    nome_fallback = _capturar_nome_cliente(session, codigo_cliente, documento)

    if nome_fallback:
        logger.add(0, f"Nome do cliente identificado por fallback: {nome_fallback}")

    return nome_fallback


def _abrir_xd03(session, logger):
    logger.add(0, "Abrindo XD03...")
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nXD03"
    send_vkey_and_wait(session, "wnd[0]", 0, "wnd[1]")


def _abrir_f4(session, logger):
    logger.add(0, "Abrindo ajuda de pesquisa...")
    send_vkey_and_wait(session, "wnd[1]", 4, "wnd[2]")


def _fechar_janelas_xd03(session, progress_callback=None, notify=True):
    if notify:
        notificar_progresso(
            progress_callback,
            "XD03",
            "processando",
            "Fechando janelas da verificação XD03...",
            97,
        )

    for window_id in ("wnd[2]", "wnd[1]"):
        try:
            session.findById(window_id).sendVKey(12)
        except Exception:
            pass

    for element_id in (
        "wnd[2]/tbar[0]/btn[12]",
        "wnd[2]/tbar[0]/btn[0]",
        "wnd[1]/tbar[0]/btn[12]",
        "wnd[1]/usr/btnSPOP-OPTION2",
    ):
        try:
            session.findById(element_id).press()
        except Exception:
            continue


def _retornar_tela_inicial_xd03(session, progress_callback=None, notify=True):
    # Mantido o nome da função para não quebrar chamadas existentes.
    # Antes esta função usava /n e forçava o SAP a voltar para o Easy Access.
    # Agora ela apenas fecha as janelas auxiliares da XD03, deixando o SAP pronto
    # para o controller seguir para a próxima etapa, como VA01.
    _fechar_janelas_xd03(
        session,
        progress_callback=progress_callback,
        notify=notify,
    )


def _ler_setores_atividade_cliente(session, logger, progress_callback=None):
    notificar_progresso(
        progress_callback,
        "XD03",
        "processando",
        "Abrindo áreas de vendas do cliente...",
        88,
    )

    wait_for_element(session, _BOTAO_AREAS_CLIENTE, timeout=8).press()
    wait_for_element(session, _TABELA_AREAS_CLIENTE, timeout=8)

    notificar_progresso(
        progress_callback,
        "XD03",
        "processando",
        "Lendo tipos habilitados para o cliente...",
        92,
    )

    setores = []

    for linha in range(0, 25):
        try:
            campo_codigo = session.findById(
                f"{_TABELA_AREAS_CLIENTE}/ctxtRF02D-SPAKU[4,{linha}]"
            )
        except Exception:
            continue

        codigo = _ler_texto(campo_codigo).upper()

        if not codigo:
            continue

        descricao = ""

        try:
            campo_descricao = session.findById(
                f"{_TABELA_AREAS_CLIENTE}/txtTSPAT-VTEXT[5,{linha}]"
            )
            descricao = _ler_texto(campo_descricao)
        except Exception:
            pass

        setores.append(
            {
                "codigo": codigo,
                "descricao": descricao,
                "tipo": _SETOR_PARA_TIPO.get(codigo),
            }
        )

    logger.add(0, f"Setores de atividade encontrados: {setores}")
    return setores


def _validar_suporte_tipo(setores, tipo_solicitacao):
    setores_necessarios = _setores_necessarios(tipo_solicitacao)

    codigos_disponiveis = {
        str(setor.get("codigo") or "").strip().upper()
        for setor in setores
    }

    return all(setor in codigos_disponiveis for setor in setores_necessarios)


def _setores_necessarios(tipo_solicitacao):
    setor = _TIPO_PARA_SETOR[tipo_solicitacao]

    if isinstance(setor, (tuple, list, set)):
        return tuple(str(item).strip().upper() for item in setor)

    return (str(setor).strip().upper(),)


def _tipos_suportados_por_setor(setores):
    tipos = []

    for setor in setores:
        tipo = _SETOR_PARA_TIPO.get(
            str(setor.get("codigo") or "").strip().upper()
        )

        if tipo and tipo not in tipos:
            tipos.append(tipo)

    return tipos


def _formatar_tipos_suportados(tipos_suportados):
    if not tipos_suportados:
        return "nenhum tipo conhecido"

    return ", ".join(_TIPO_LABEL.get(tipo, tipo) for tipo in tipos_suportados)


def _buscar(session, campo, doc, logger, tipo, progress_callback=None):
    campo_input = wait_for_element(session, campo)
    campo_input.text = doc

    logger.add(0, f"Pesquisando {tipo.upper()}: {doc}")

    notificar_progresso(
        progress_callback,
        "XD03",
        "processando",
        f"Consultando {tipo.upper()} no SAP...",
        58,
    )

    press_and_wait(session, "wnd[2]/tbar[0]/btn[0]")

    if element_exists(session, campo):
        logger.add(0, f"{tipo.upper()} não encontrado")

        notificar_progresso(
            progress_callback,
            "XD03",
            "erro",
            f"{tipo.upper()} não encontrado no SAP.",
            58,
        )

        press_and_wait(session, "wnd[2]/tbar[0]/btn[12]")
        press_and_wait(session, "wnd[1]/tbar[0]/btn[12]")

        resultado = resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Cliente nao encontrado",
            dados={
                "documento": doc,
                "tipo_documento": tipo,
            },
        )
        resultado["acao_pendente"] = {
            "tipo": "cliente_nao_cadastrado",
            "documento": doc,
            "tipo_documento": tipo,
            "mensagem": "Cliente nao cadastrado no SAP.",
        }
        return resultado

    notificar_progresso(
        progress_callback,
        "XD03",
        "processando",
        "Confirmando resultado da busca...",
        84,
    )

    press_and_wait(session, "wnd[2]/tbar[0]/btn[0]")

    campo_cliente = wait_for_element(session, _CAMPO_CLIENTE)
    codigo = campo_cliente.text.strip()

    if not codigo:
        notificar_progresso(
            progress_callback,
            "XD03",
            "erro",
            "Código do cliente vazio na XD03.",
            84,
        )

        return resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Código do cliente vazio",
        )

    logger.add(0, f"Cliente encontrado: {codigo}")
    nome_cliente = _capturar_nome_cliente(session, codigo, doc)

    if nome_cliente:
        logger.add(0, f"Nome do cliente identificado: {nome_cliente}")

    notificar_progresso(
        progress_callback,
        "XD03",
        "processando",
        f"Cliente {codigo} encontrado. Verificando tipo solicitado...",
        86,
    )

    return resultado_padrao(
        ok=True,
        etapa="XD03",
        mensagem="Cliente encontrado",
        dados={
            "cliente": codigo,
            "documento": doc,
            "tipo_documento": tipo,
            "nome_cliente": nome_cliente,
        },
    )


def buscar_cliente(session, dados, logger, progress_callback=None):
    try:
        doc = limpar_doc(dados["doc"])
        tipo_doc = tipo_documento(doc)
        tipo_solicitacao = _normalizar_tipo_solicitacao(dados.get("tipo"))

        notificar_progresso(
            progress_callback,
            "XD03",
            "processando",
            "Preparando busca do cliente...",
            8,
        )

        cliente_cache = cache_cliente.get(doc)

        if cliente_cache:
            logger.add(
                0,
                "Cliente encontrado no cache. Validando área de vendas no SAP...",
            )
        else:
            logger.add(0, "Cliente não encontrado no cache. Consultando SAP...")

        notificar_progresso(
            progress_callback,
            "XD03",
            "processando",
            "Abrindo transação XD03...",
            18,
        )

        _abrir_xd03(session, logger)

        if cliente_cache and cliente_cache.get("cliente"):
            notificar_progresso(
                progress_callback,
                "XD03",
                "processando",
                "Aplicando cliente recuperado e verificando áreas...",
                34,
            )

            codigo_cliente = str(cliente_cache["cliente"]).strip()
            wait_for_element(session, _CAMPO_CLIENTE, timeout=8).text = codigo_cliente

            resultado = resultado_padrao(
                ok=True,
                etapa="XD03",
                mensagem="Cliente recuperado do cache",
                dados={
                    "cliente": codigo_cliente,
                    "documento": doc,
                    "tipo_documento": cliente_cache.get("tipo_documento") or tipo_doc,
                    "nome_cliente": cliente_cache.get("nome_cliente"),
                },
            )

            if not resultado["dados"].get("nome_cliente"):
                nome_cliente = _capturar_nome_cliente(session, codigo_cliente, doc)
                if nome_cliente:
                    resultado["dados"]["nome_cliente"] = nome_cliente

        else:
            notificar_progresso(
                progress_callback,
                "XD03",
                "processando",
                "Abrindo pesquisa de cliente...",
                34,
            )

            _abrir_f4(session, logger)

            if tipo_doc == "cnpj":
                resultado = _buscar(
                    session,
                    _CAMPO_CNPJ,
                    doc,
                    logger,
                    "cnpj",
                    progress_callback=progress_callback,
                )
            else:
                resultado = _buscar(
                    session,
                    _CAMPO_CPF,
                    doc,
                    logger,
                    "cpf",
                    progress_callback=progress_callback,
                )

        if resultado["ok"]:
            setores = _ler_setores_atividade_cliente(
                session,
                logger,
                progress_callback=progress_callback,
            )

            tipos_suportados = _tipos_suportados_por_setor(setores)

            resultado["dados"]["setores_atividade"] = setores
            resultado["dados"]["tipos_suportados"] = tipos_suportados

            if not _validar_suporte_tipo(setores, tipo_solicitacao):
                tipo_label = _TIPO_LABEL.get(tipo_solicitacao, tipo_solicitacao)
                setor_necessario = " + ".join(_setores_necessarios(tipo_solicitacao))
                disponiveis = _formatar_tipos_suportados(tipos_suportados)

                mensagem = (
                    f"O tipo selecionado ({tipo_label}) não existe para o cliente informado "
                    f"(setor {setor_necessario}). Tipos disponíveis: {disponiveis}. "
                    "Solicite a criação da área de vendas para este cliente e retorne ao processo."
                )

                logger.add(0, mensagem, nivel="ERRO", publico=True)

                notificar_progresso(
                    progress_callback,
                    "XD03",
                    "erro",
                    mensagem,
                    95,
                )

                _retornar_tela_inicial_xd03(
                    session,
                    progress_callback=progress_callback,
                    notify=False,
                )

                pendencia = {
                    "tipo": "setor_ausente",
                    "cliente": resultado["dados"].get("cliente"),
                    "documento": doc,
                    "tipo_documento": resultado["dados"].get("tipo_documento") or tipo_doc,
                    "tipo_solicitacao": tipo_solicitacao,
                    "tipo_label": tipo_label,
                    "setores_necessarios": list(_setores_necessarios(tipo_solicitacao)),
                    "setores_encontrados": setores,
                    "tipos_suportados": tipos_suportados,
                    "mensagem": mensagem,
                }

                retorno = resultado_padrao(
                    ok=False,
                    etapa="XD03",
                    mensagem=mensagem,
                    dados=resultado["dados"],
                    erro_tecnico=(
                        f"Setor necessario: {setor_necessario}; "
                        f"setores encontrados: {setores}"
                    ),
                )
                retorno["acao_pendente"] = pendencia
                return retorno

            tipo_label = _TIPO_LABEL.get(tipo_solicitacao, tipo_solicitacao)

            notificar_progresso(
                progress_callback,
                "XD03",
                "processando",
                f"Tipo {tipo_label} confirmado para o cliente.",
                96,
            )

            nome_cliente = _capturar_nome_cliente_dados_gerais(
                session,
                resultado["dados"]["cliente"],
                doc,
                logger,
                progress_callback=progress_callback,
            )

            if nome_cliente:
                resultado["dados"]["nome_cliente"] = nome_cliente

            cache_cliente.set(doc, resultado["dados"])
            logger.add(0, "Cliente salvo no cache")

            _retornar_tela_inicial_xd03(
                session,
                progress_callback=progress_callback,
            )

            notificar_progresso(
                progress_callback,
                "XD03",
                "concluido",
                "Cliente localizado e confirmado.",
                100,
            )

        return resultado

    except Exception as e:
        try:
            _retornar_tela_inicial_xd03(
                session,
                progress_callback=progress_callback,
                notify=False,
            )
        except Exception:
            pass

        logger.add(0, f"Erro XD03: {e}")

        notificar_progresso(
            progress_callback,
            "XD03",
            "erro",
            "Falha ao buscar cliente no XD03.",
        )

        return resultado_padrao(
            ok=False,
            etapa="XD03",
            mensagem="Erro ao buscar cliente",
            erro_tecnico=str(e),
        )
