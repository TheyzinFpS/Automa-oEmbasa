import json
import re
from datetime import datetime

from backend.flows.f110 import f110
from backend.flows.f110_boleto import selecionar_boletos_sp02
from backend.flows.va01 import criar_pedido
from backend.flows.vf01 import criar_doc_faturamento
from backend.flows.vf02 import pos_faturamento
from backend.flows.xd03 import buscar_cliente
from backend.sap_connection import conectar_sap
from backend.utils.sap_sessions import (
    garantir_sessao_transacao,
    obter_transacao,
)
from backend.utils.sap_waits import (
    fechar_janelas_secundarias,
)


STAGE_ORDER = [
    "XD03",
    "VA01",
    "VF01",
    "FB03",
    "VF02_RESALVAR",
    "F110",
]

STAGE_TRANSACTION = {
    "XD03": "XD03",
    "VA01": "VA01",
    "VF01": "VF01",
    "FB03": "FB03",
    "VF02_RESALVAR": "VF02",
    "F110": "F110",
}

TIPO_COMPOSTO_AGUA_ESGOTO = "agua_esgoto"
TIPOS_AGUA_ESGOTO = ("agua", "esgoto")
TIPO_LABEL = {
    "agua": "Água",
    "esgoto": "Esgoto",
    "agua_esgoto": "Água + Esgoto",
}

ETAPA_DIAGNOSTICO = {
    "XD03": {
        "nome": "Buscar cliente",
        "acao": "buscar o cliente no XD03",
        "problema": "cliente não localizado, setor de atividade ausente ou SAP fora da tela esperada",
        "solucao": "confira o documento informado, o cadastro do cliente e os setores AG/EG no SAP",
    },
    "VA01": {
        "nome": "Criar pedido",
        "acao": "criar o pedido com cliente, tipo, valor e endereço do empreendimento",
        "problema": "cliente, valor, tipo ou endereço não aceito pela VA01",
        "solucao": "confira os dados do empreendimento, o valor e mensagens exibidas na VA01",
    },
    "VF01": {
        "nome": "Criar doc.fat.",
        "acao": "criar o documento de faturamento a partir do pedido gerado",
        "problema": "pedido não disponível para faturamento ou popup bloqueando a VF01",
        "solucao": "confira se o pedido foi criado e se existe aviso pendente na VF01",
    },
    "FB03": {
        "nome": "Ajustar contábil",
        "acao": "abrir o faturamento no FB03 e aplicar o ajuste contábil",
        "problema": "doc.fat não encontrado, tela incorreta ou bloqueio no ajuste contábil",
        "solucao": "confira o doc.fat gerado e a mensagem exibida na FB03",
    },
    "VF02_RESALVAR": {
        "nome": "Salvar faturamento",
        "acao": "retornar à VF02 e re-salvar o faturamento ajustado",
        "problema": "faturamento bloqueado, tela diferente ou popup impedindo o salvamento",
        "solucao": "confira se o faturamento está aberto para edição e feche avisos pendentes",
    },
    "F110": {
        "nome": "Gerar pagamento",
        "acao": "executar a F110",
        "problema": "cliente/doc.fat incorreto, BOL indisponível, variante ou spool não acessível",
        "solucao": "confira cliente, doc.fat, BOL disponível e mensagens da F110/SP02",
    },
    "CONEXAO": {
        "nome": "Conectar ao SAP",
        "acao": "conectar na sessão SAP GUI já logada",
        "problema": "SAP fechado, usuário sem login ou SAP GUI Scripting indisponível",
        "solucao": "abra o SAP, faça login e tente novamente",
    },
}


def _extrair_numero_sap(texto):
    numeros = re.findall(r"\b\d{6,12}\b", str(texto or ""))
    return numeros[-1] if numeros else ""


# Modelo unico de resposta para todas as etapas do fluxo SAP.
def resultado_padrao(ok, etapa, mensagem, dados=None, erro_tecnico=None):
    return {
        "ok": ok,
        "etapa": etapa,
        "mensagem": mensagem,
        "dados": dados,
        "erro_tecnico": erro_tecnico,
    }


# Orquestra a automacao completa na ordem correta e guarda contexto para retomada.
class SAPController:
    def __init__(self, logger):
        self.logger = logger

    # Envia progresso para a interface sem deixar erro visual parar o fluxo SAP.
    def _notificar_progresso(
        self,
        progress_callback,
        etapa,
        status,
        mensagem=None,
        percentual=None,
    ):
        if not callable(progress_callback):
            return

        try:
            progress_callback(etapa, status, mensagem, percentual)
        except Exception:
            return

    # Converte o nome da etapa em índice para comparar a ordem de execução.
    def _indice_etapa(self, etapa):
        try:
            return STAGE_ORDER.index(str(etapa or "").strip().upper())
        except ValueError:
            return -1

    # Decide se uma etapa deve rodar quando o usuário retoma de um checkpoint.
    def _deve_executar(self, etapa, iniciar_em):
        indice_etapa = self._indice_etapa(etapa)
        indice_inicio = self._indice_etapa(iniciar_em)

        if indice_etapa == -1 or indice_inicio == -1:
            return True

        return indice_etapa >= indice_inicio

    # Normaliza o checkpoint recebido do frontend para evitar retomada invalida.
    def _normalizar_checkpoint(self, checkpoint):
        if isinstance(checkpoint, str):
            try:
                checkpoint = json.loads(checkpoint)
            except Exception:
                checkpoint = None

        if not isinstance(checkpoint, dict):
            return "XD03", {}

        iniciar_em = str(checkpoint.get("resume_from") or "XD03").strip().upper()
        contexto = dict(
            checkpoint.get("contexto")
            or checkpoint.get("dados")
            or checkpoint.get("resultado")
            or {}
        )

        if self._indice_etapa(iniciar_em) == -1:
            iniciar_em = "XD03"

        return iniciar_em, contexto

    # Marca visualmente como concluidas as etapas anteriores ao ponto retomado.
    def _sincronizar_progresso_retomada(self, progress_callback, iniciar_em):
        indice_inicio = self._indice_etapa(iniciar_em)

        if indice_inicio <= 0:
            return

        for etapa in STAGE_ORDER[:indice_inicio]:
            self._notificar_progresso(
                progress_callback,
                etapa,
                "concluido",
                "Etapa já concluída antes da retomada.",
                100,
            )

    # Fecha popups simples antes de retomar, sem mandar o SAP para Easy Access.
    def _fechar_popups_retomada(self, session):
        self._garantir_janela_unica_sap(session, origem="retomada")

    # Garante que a etapa seguinte comece com apenas a janela principal wnd[0].
    def _garantir_janela_unica_sap(self, session, origem=""):
        try:
            fechadas = fechar_janelas_secundarias(session)
        except Exception as exc:
            self.logger.add(
                -1,
                f"Não foi possível limpar janelas secundárias do SAP ({origem}): {exc}",
                nivel="DEBUG",
            )
            return 0

        if fechadas:
            self.logger.add(
                -1,
                f"Janelas secundárias SAP fechadas após {origem}: {fechadas}",
                nivel="DEBUG",
            )

        return fechadas

    # Ao retomar, prioriza uma sessao SAP que ja esteja na transacao pendente.
    def _preparar_tela_para_retomada(self, session, iniciar_em, progress_callback=None):
        transacao = STAGE_TRANSACTION.get(str(iniciar_em or "").strip().upper())

        if not transacao:
            return session

        self._notificar_progresso(
            progress_callback,
            iniciar_em,
            "processando",
            f"Preparando retomada em {iniciar_em}...",
            3,
        )

        try:
            self._fechar_popups_retomada(session)
            transacao_antes = obter_transacao(session)
            session = garantir_sessao_transacao(
                session,
                transacao,
                preferir_existente=True,
                abrir_se_necessario=True,
            )
            transacao_depois = obter_transacao(session)
            self.logger.add(
                -1,
                (
                    f"SAP preparado para retomar {iniciar_em}. "
                    f"Transacao antes: {transacao_antes or 'indefinida'}; "
                    f"agora: {transacao_depois or transacao}."
                ),
            )
            return session
        except Exception as exc:
            self.logger.add(
                -1,
                f"Não foi possível reposicionar SAP antes da retomada: {exc}",
                nivel="DEBUG",
            )
            return session

    # Monta apenas os dados seguros/uteis para mostrar na interface.
    def _montar_dados_publicos(self, dados, contexto):
        retorno = {
            "cliente": contexto.get("cliente"),
            "nome_cliente": contexto.get("nome_cliente"),
            "pedido": contexto.get("pedido"),
            "pedido_agua": contexto.get("pedido_agua"),
            "pedido_esgoto": contexto.get("pedido_esgoto"),
            "faturamento": contexto.get("faturamento"),
            "doc_fat": contexto.get("doc_fat"),
            "doc_fat_agua": contexto.get("doc_fat_agua"),
            "doc_fat_esgoto": contexto.get("doc_fat_esgoto"),
            "boleto": contexto.get("boleto"),
            "identificacao_pagamento": contexto.get("identificacao_pagamento"),
            "identificacoes_pagamento": contexto.get("identificacoes_pagamento"),
            "agua_esgoto": contexto.get("agua_esgoto"),
            "nomes_pdf_sugeridos": contexto.get("nomes_pdf_sugeridos"),
            "spools_boletos": contexto.get("spools_boletos"),
            "documento": dados["doc"],
            "tipo_documento": dados["doc_info"]["rotulo"],
            "tipo": dados.get("tipo"),
            "valor": dados["valor_info"]["formatado"],
            "endereco": dados.get("endereco") or {},
        }

        return {
            chave: valor
            for chave, valor in retorno.items()
            if valor not in (None, "")
        }

    # Cria um ponto de retomada para continuar depois de uma falha corrigida no SAP.
    def _montar_checkpoint(self, resume_from, dados, contexto):
        return {
            "resume_from": resume_from,
            "criado_em": datetime.now().isoformat(timespec="seconds"),
            "contexto": self._montar_dados_publicos(dados, contexto),
            "orientacao": (
                "Confira a tela do SAP, corrija o problema da etapa indicada "
                "e use a retomada para continuar sem reiniciar as etapas anteriores."
            ),
        }

    def _classificar_erro_operacional(self, etapa, detalhe, meta):
        texto = str(detalhe or "").lower()
        problema_padrao = meta.get("problema") or "bloqueio não classificado na etapa atual"
        solucao_padrao = meta.get("solucao") or "confira a tela atual do SAP e tente novamente"

        regras = [
            (
                (
                    "sessão logada",
                    "sessao logada",
                    "localizar uma sessão",
                    "localizar uma sessao",
                    "localizar uma sess",
                    "sess",
                ),
                "SAP não está aberto, usuário não fez login ou a sessão SAP não está disponível para automação",
                "abra o SAP, faça login e tente novamente",
            ),
            (
                ("scripting", "sap gui scripting"),
                "SAP GUI Scripting pode estar desabilitado ou bloqueado para o usuário",
                "habilite/verifique o SAP GUI Scripting e tente novamente",
            ),
            (
                ("cliente não encontrado", "cliente nao encontrado", "nenhum cliente"),
                "documento não localizado no cadastro de clientes",
                "confira o CPF/CNPJ informado e valide o cadastro no XD03",
            ),
            (
                ("setor", "atividade", "ag e eg", "ag/eg"),
                "cliente encontrado, mas setor de atividade esperado não foi confirmado",
                "confira se o cliente possui os setores AG e/ou EG liberados no SAP",
            ),
            (
                ("timeout", "não foi possível encontrar", "nao foi possivel encontrar", "findbyid", "element"),
                "SAP ficou em tela diferente, demorou a responder ou algum campo/popup não apareceu",
                "confira a tela atual do SAP, feche popups pendentes e retome da etapa indicada",
            ),
            (
                ("doc_fat", "faturamento", "documento de faturamento"),
                "documento de faturamento não foi capturado ou não está disponível para a próxima etapa",
                "confira a etapa VF01/VF02 e valide o número do doc.fat antes de retomar",
            ),
            (
                ("bol", "identificação", "identificacao"),
                "identificação BOL pode estar ocupada ou indisponível",
                "confira as BOLs do dia na F110 e libere/avance para uma identificação disponível",
            ),
            (
                ("sp02", "spool", "boleto"),
                "spool do boleto não foi encontrada ou a SP02 não está na ordem esperada",
                "confira se o boleto foi gerado e se a SP02 mostra as linhas BOLETO em ordem decrescente",
            ),
            (
                ("aviso operacional", "confirmado pelo usuário", "confirmado pelo usuario"),
                "o modal de cópia não foi confirmado dentro do tempo esperado",
                "clique em Copiar nome e fechar quando o modal aparecer",
            ),
        ]

        for termos, problema, solucao in regras:
            if any(termo in texto for termo in termos):
                return problema, solucao

        return problema_padrao, solucao_padrao

    def _acao_tentada_erro(self, etapa, detalhe, meta):
        texto = str(detalhe or "").lower()

        if any(
            termo in texto
            for termo in (
                "sessão logada",
                "sessao logada",
                "localizar uma sessão",
                "localizar uma sessao",
                "localizar uma sess",
            )
        ):
            return "conectar em uma sessão SAP logada"

        etapa = str(etapa or "").strip().upper()

        if etapa == "XD03":
            if any(termo in texto for termo in ("nome do cliente", "nome identificado", "razao", "razão")):
                return "capturar o nome do cliente no XD03"

            if any(termo in texto for termo in ("setor", "atividade", "ag e eg", "ag/eg")):
                return "validar o setor de atividade do cliente"

            if any(termo in texto for termo in ("f4", "ajuda de pesquisa", "matchcode")):
                return "abrir a ajuda de pesquisa do XD03"

            return "buscar o cliente pelo CPF/CNPJ"

        if etapa == "VA01":
            if any(termo in texto for termo in ("valor", "montante", "preço", "preco")):
                return "preencher o valor do pedido na VA01"

            if any(termo in texto for termo in ("endereço", "endereco", "rua", "cep", "bairro")):
                return "preencher o endereço do empreendimento na VA01"

            if any(termo in texto for termo in ("salvar", "ordem", "pedido")):
                return "salvar o pedido na VA01"

            return "criar o pedido na VA01"

        if etapa == "VF01":
            return "criar o documento de faturamento na VF01"

        if etapa == "FB03":
            return "aplicar o ajuste contábil no faturamento"

        if etapa == "VF02_RESALVAR":
            return "re-salvar o faturamento na VF02"

        if etapa == "F110":
            if any(termo in texto for termo in ("bol", "identificação", "identificacao")):
                return "gerar ou selecionar a identificação BOL da F110"

            if any(termo in texto for termo in ("seleção livre", "selecao livre", "doc_fat", "doc.fat")):
                return "preencher a seleção livre da F110 com o doc.fat"

            if any(termo in texto for termo in ("meio de pagamento", "arquivo de pagamento")):
                return "gerar o meio de pagamento"

            if any(termo in texto for termo in ("sp02", "spool", "boleto")):
                return "localizar ou selecionar o boleto na SP02"

            return "executar a F110"

        return meta.get("acao") or "executar a etapa atual do fluxo SAP"

    def _resumir_detalhe_erro(self, texto, limite=180):
        linhas = [
            linha.strip()
            for linha in str(texto or "").replace("\r", "\n").split("\n")
            if linha.strip()
        ]
        resumo = linhas[0] if linhas else "sem detalhe técnico retornado"
        resumo = re.sub(r"\s+", " ", resumo).strip().rstrip(".")

        if len(resumo) > limite:
            resumo = resumo[: limite - 3].rstrip() + "..."

        return resumo

    def _montar_log_falha_detalhado(
        self,
        etapa,
        mensagem,
        erro_tecnico,
        dados,
        contexto,
        resume_from=None,
        session=None,
    ):
        etapa_chave = str(etapa or "").strip().upper() or "INDEFINIDA"
        meta = ETAPA_DIAGNOSTICO.get(etapa_chave, {})
        nome_etapa = meta.get("nome") or etapa_chave
        mensagem_usuario = str(
            mensagem or "sem mensagem de usuário retornada"
        ).strip().rstrip(".")
        detalhe_completo = str(
            erro_tecnico or mensagem or "sem detalhe técnico retornado"
        ).strip().rstrip(".")
        detalhe = self._resumir_detalhe_erro(detalhe_completo)
        acao = self._acao_tentada_erro(etapa_chave, detalhe_completo, meta)
        problema, solucao = self._classificar_erro_operacional(
            etapa_chave,
            detalhe_completo,
            meta,
        )
        transacao = ""

        if session is not None:
            try:
                transacao = obter_transacao(session)
            except Exception:
                transacao = ""

        linhas = [
            f"Falha em {etapa_chave} - {nome_etapa}.",
            f"- Sistema tentou executar: {acao}.",
            f"- Qual foi o erro: {detalhe or mensagem_usuario}.",
            f"- Possível problema: {problema}.",
            f"- Possível solução: {solucao}.",
        ]

        if transacao:
            linhas.append(f"- Tela SAP detectada: {transacao}.")

        if resume_from:
            linhas.append(
                f"- Retomada: corrigir no SAP e continuar a partir de {resume_from}."
            )

        return "\n".join(linhas)

    # Centraliza resposta de erro e inclui checkpoint quando a etapa pode ser retomada.
    def _falha(
        self,
        etapa,
        mensagem,
        erro_tecnico,
        dados,
        contexto,
        resume_from=None,
        session=None,
    ):
        self.logger.add(
            -1,
            self._montar_log_falha_detalhado(
                etapa,
                mensagem,
                erro_tecnico,
                dados,
                contexto,
                resume_from=resume_from,
                session=session,
            ),
            nivel="ERRO",
            publico=True,
        )
        payload = resultado_padrao(
            ok=False,
            etapa=etapa,
            mensagem=mensagem,
            dados=self._montar_dados_publicos(dados, contexto),
            erro_tecnico=erro_tecnico,
        )

        if resume_from:
            payload["checkpoint"] = self._montar_checkpoint(
                resume_from,
                dados,
                contexto,
            )

        return payload

    # Monta resumo legivel do cancelamento para logs e interface.
    def _resumo_cancelamento(self, etapa, dados, contexto):
        dados_publicos = self._montar_dados_publicos(dados, contexto)
        endereco = dados.get("endereco") or {}
        colocados = []
        pendentes = []

        if dados_publicos.get("documento"):
            colocados.append(f"documento {dados_publicos['documento']}")

        if dados.get("tipo"):
            colocados.append(f"tipo {dados.get('tipo')}")

        if dados_publicos.get("valor"):
            colocados.append(f"valor {dados_publicos['valor']}")

        if endereco.get("empreendimento"):
            colocados.append(f"empreendimento {endereco.get('empreendimento')}")

        if contexto.get("cliente"):
            colocados.append(f"cliente {contexto['cliente']}")
        else:
            pendentes.append("código do cliente")

        if contexto.get("faturamento") or contexto.get("doc_fat"):
            colocados.append(
                f"doc.fat {contexto.get('doc_fat') or contexto.get('faturamento')}"
            )
        else:
            pendentes.append("documento de faturamento")

        if contexto.get("identificacao_pagamento") or contexto.get("boleto"):
            colocados.append(
                f"pagamento {contexto.get('identificacao_pagamento') or contexto.get('boleto')}"
            )
        else:
            pendentes.append("boleto/F110")

        return {
            **dados_publicos,
            "ultima_etapa": etapa,
            "dados_colocados": colocados,
            "dados_pendentes": pendentes,
        }

    # Retorna cancelamento padronizado quando o usuário pediu parada segura.
    def _cancelado(self, etapa, dados, contexto, progress_callback=None):
        resumo = self._resumo_cancelamento(etapa, dados, contexto)
        colocados = ", ".join(resumo["dados_colocados"]) or "nenhum dado confirmado"
        pendentes = ", ".join(resumo["dados_pendentes"]) or "nenhum dado pendente"
        mensagem = (
            f"Criação do boleto cancelada pelo usuário. Última função acessada: {etapa}. "
            f"Dados já confirmados: {colocados}. Dados pendentes: {pendentes}."
        )

        self.logger.add(-1, mensagem, nivel="ERRO", publico=True)
        self._notificar_progresso(
            progress_callback,
            etapa,
            "erro",
            "Processo cancelado pelo usuário.",
        )

        payload = resultado_padrao(
            ok=False,
            etapa=etapa,
            mensagem=mensagem,
            dados=resumo,
            erro_tecnico="Cancelamento solicitado pelo usuário.",
        )
        payload["cancelado"] = True
        payload["checkpoint"] = self._montar_checkpoint(etapa, dados, contexto)
        return payload

    # Verifica o sinal de cancelamento apenas entre pontos seguros do fluxo.
    def _verificar_cancelamento(
        self,
        cancel_event,
        etapa,
        dados,
        contexto,
        progress_callback=None,
    ):
        if cancel_event is not None and cancel_event.is_set():
            return self._cancelado(
                etapa,
                dados,
                contexto,
                progress_callback=progress_callback,
            )

        return None

    def _progress_callback_tipo(self, progress_callback, tipo_label):
        if not callable(progress_callback):
            return None

        label = str(tipo_label or "").strip()
        mensagens = {
            "VA01": f"Criando Pedido {label}",
            "VF01": f"Criando doc.fat {label}",
            "FB03": f"Ajustando contábil {label}",
            "VF02_RESALVAR": f"Salvando faturamento {label}",
            "F110": f"Gerando pagamento {label}",
        }

        def callback(etapa, status, mensagem=None, percentual=None):
            etapa_chave = str(etapa or "").strip().upper()
            status_chave = str(status or "").strip().lower()
            mensagem_base = mensagens.get(etapa_chave)
            mensagem_final = mensagem

            if mensagem_base and status_chave in {
                "processando",
                "processing",
                "running",
                "ativo",
                "active",
            }:
                mensagem_final = mensagem_base
            elif mensagem_base and status_chave in {
                "concluido",
                "concluida",
                "concluído",
                "concluída",
                "done",
                "success",
                "sucesso",
            }:
                mensagem_final = f"{mensagem_base} concluído"

            progress_callback(etapa, status, mensagem_final, percentual)

        return callback

    def _dados_com_tipo(self, dados, tipo):
        dados_tipo = dict(dados)
        dados_tipo["tipo"] = tipo
        return dados_tipo

    def _executar_criacao_ate_vf02(
        self,
        session,
        dados_tipo,
        contexto_base,
        cancel_event=None,
        progress_callback=None,
    ):
        tipo = str(dados_tipo.get("tipo") or "").strip().lower()
        tipo_label = TIPO_LABEL.get(tipo, tipo)
        contexto = dict(contexto_base)
        progress_tipo = self._progress_callback_tipo(progress_callback, tipo_label)

        self.logger.add(-1, f"Iniciando criação do pedido de {tipo_label}.", publico=True)
        self._notificar_progresso(
            progress_tipo,
            "VA01",
            "processando",
            None,
            5,
        )

        cancelado = self._verificar_cancelamento(
            cancel_event,
            "VA01",
            dados_tipo,
            contexto,
            progress_callback=progress_tipo,
        )

        if cancelado:
            return cancelado, None

        resultado_va01 = criar_pedido(
            session,
            dados_tipo,
            contexto["cliente"],
            self.logger,
            progress_callback=progress_tipo,
        )

        if not resultado_va01["ok"]:
            return self._falha(
                etapa="VA01",
                mensagem=resultado_va01["mensagem"],
                erro_tecnico=resultado_va01.get("erro_tecnico"),
                dados=dados_tipo,
                contexto=contexto,
                resume_from="VA01",
                session=session,
            ), None

        dados_va01 = resultado_va01.get("dados") or {}
        pedido = (
            dados_va01.get("pedido")
            or dados_va01.get("ordem")
            or _extrair_numero_sap(dados_va01.get("status_sap"))
            or ""
        )
        contexto["pedido"] = pedido
        self._garantir_janela_unica_sap(session, origem=f"VA01 {tipo_label}")

        cancelado = self._verificar_cancelamento(
            cancel_event,
            "VF01",
            dados_tipo,
            contexto,
            progress_callback=progress_tipo,
        )

        if cancelado:
            return cancelado, None

        resultado_vf01 = criar_doc_faturamento(
            session,
            self.logger,
            progress_callback=progress_tipo,
        )

        if not resultado_vf01["ok"]:
            return self._falha(
                etapa="VF01",
                mensagem=resultado_vf01["mensagem"],
                erro_tecnico=resultado_vf01.get("erro_tecnico"),
                dados=dados_tipo,
                contexto=contexto,
                resume_from="VF01",
                session=session,
            ), None

        faturamento = resultado_vf01["dados"]["faturamento"]
        doc_fat = (
            resultado_vf01["dados"].get("doc_fat")
            or resultado_vf01["dados"].get("faturamento")
            or faturamento
        )
        contexto["faturamento"] = faturamento
        contexto["doc_fat"] = doc_fat
        self._garantir_janela_unica_sap(session, origem=f"VF01 {tipo_label}")

        cancelado = self._verificar_cancelamento(
            cancel_event,
            "FB03",
            dados_tipo,
            contexto,
            progress_callback=progress_tipo,
        )

        if cancelado:
            return cancelado, None

        resultado_vf02 = pos_faturamento(
            session,
            faturamento,
            self.logger,
            progress_callback=progress_tipo,
            start_from="FB03",
        )

        if not resultado_vf02["ok"]:
            contexto["faturamento"] = (
                (resultado_vf02.get("dados") or {}).get("faturamento")
                or contexto.get("faturamento")
            )

            return self._falha(
                etapa=resultado_vf02.get("etapa") or "FB03",
                mensagem=resultado_vf02["mensagem"],
                erro_tecnico=resultado_vf02.get("erro_tecnico"),
                dados=dados_tipo,
                contexto=contexto,
                resume_from=resultado_vf02.get("etapa") or "FB03",
                session=session,
            ), None

        faturamento = resultado_vf02["dados"]["faturamento"]
        contexto["faturamento"] = faturamento
        self._garantir_janela_unica_sap(session, origem=f"FB03/VF02 {tipo_label}")

        item = {
            "tipo": tipo,
            "tipo_label": tipo_label,
            "pedido": pedido,
            "faturamento": faturamento,
            "doc_fat": doc_fat,
            "dados": {
                **dados_tipo,
                "nome_cliente": contexto_base.get("nome_cliente"),
            },
        }
        self.logger.add(
            -1,
            f"{tipo_label} criado até o re-salvamento. Doc.fat: {doc_fat}.",
            publico=True,
        )
        return None, item

    def _executar_fluxo_agua_esgoto(
        self,
        dados,
        progress_callback=None,
        notice_callback=None,
        resume_checkpoint=None,
        cancel_event=None,
    ):
        if resume_checkpoint:
            self.logger.add(
                -1,
                "Retomada do tipo Água + Esgoto ainda reinicia pelo ponto seguro do fluxo composto.",
                nivel="AVISO",
                publico=True,
            )

        contexto = {
            "cliente": None,
            "nome_cliente": None,
            "pedido": None,
            "faturamento": None,
            "doc_fat": None,
            "boleto": None,
            "identificacao_pagamento": None,
        }
        etapa_atual = "CONEXAO"
        session = None

        try:
            self.logger.add(-1, "Conectando ao SAP...", publico=True)
            self.logger.add(-1, "Fluxo composto selecionado: Água + Esgoto.", publico=True)

            session = conectar_sap()
            self._garantir_janela_unica_sap(session, origem="conexão")

            etapa_atual = "XD03"
            cancelado = self._verificar_cancelamento(
                cancel_event,
                "XD03",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            resultado_xd03 = buscar_cliente(
                session,
                dados,
                self.logger,
                progress_callback=progress_callback,
            )

            if not resultado_xd03["ok"]:
                return self._falha(
                    etapa="XD03",
                    mensagem=resultado_xd03["mensagem"],
                    erro_tecnico=resultado_xd03.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from="XD03",
                    session=session,
                )

            contexto["cliente"] = resultado_xd03["dados"]["cliente"]
            contexto["nome_cliente"] = resultado_xd03["dados"].get("nome_cliente")
            self.logger.add(
                0,
                f"Cliente validado para Água + Esgoto: {contexto['cliente']}",
                publico=True,
            )
            self._garantir_janela_unica_sap(session, origem="XD03")

            itens = []
            itens_por_tipo = {}

            for tipo in TIPOS_AGUA_ESGOTO:
                dados_tipo = self._dados_com_tipo(dados, tipo)
                tipo_label = TIPO_LABEL.get(tipo, tipo)
                progress_tipo = self._progress_callback_tipo(
                    progress_callback,
                    tipo_label,
                )

                etapa_atual = "VA01"
                falha, item = self._executar_criacao_ate_vf02(
                    session,
                    dados_tipo,
                    contexto,
                    cancel_event=cancel_event,
                    progress_callback=progress_tipo,
                )

                if falha:
                    return falha

                itens.append(item)
                itens_por_tipo[tipo] = item
                contexto[f"pedido_{tipo}"] = item.get("pedido")
                contexto[f"doc_fat_{tipo}"] = item.get("doc_fat")

            for item in itens:
                progress_tipo = self._progress_callback_tipo(
                    progress_callback,
                    item["tipo_label"],
                )
                etapa_atual = "F110"
                cancelado = self._verificar_cancelamento(
                    cancel_event,
                    "F110",
                    item["dados"],
                    contexto,
                    progress_callback=progress_tipo,
                )

                if cancelado:
                    return cancelado

                self.logger.add(
                    6,
                    f"Iniciando F110 do pedido de {item['tipo_label']} com doc.fat {item['doc_fat']}.",
                    publico=True,
                )

                resultado_f110 = f110(
                    session,
                    contexto["cliente"],
                    item["doc_fat"],
                    self.logger,
                    progress_callback=progress_tipo,
                    notice_callback=notice_callback,
                    dados=item["dados"],
                    selecionar_boleto=False,
                )

                if not resultado_f110["ok"]:
                    contexto["doc_fat"] = item.get("doc_fat")
                    contexto["faturamento"] = item.get("faturamento")
                    return self._falha(
                        etapa="F110",
                        mensagem=resultado_f110["mensagem"],
                        erro_tecnico=resultado_f110.get("erro_tecnico"),
                        dados=item["dados"],
                        contexto=contexto,
                        resume_from="F110",
                        session=session,
                    )

                dados_f110 = resultado_f110.get("dados") or {}
                item.update(
                    {
                        "identificacao_pagamento": dados_f110.get("identificacao_pagamento"),
                        "job_name": dados_f110.get("job_name"),
                        "nome_arquivo_meio_pagamento": dados_f110.get(
                            "nome_arquivo_meio_pagamento"
                        ),
                    }
                )
                self._garantir_janela_unica_sap(
                    session,
                    origem=f"F110 {item['tipo_label']}",
                )

            boletos_para_sp02 = []

            for tipo in reversed(TIPOS_AGUA_ESGOTO):
                item = itens_por_tipo.get(tipo)

                if not item:
                    continue

                boletos_para_sp02.append(
                    {
                        "tipo": item["tipo"],
                        "doc_fat": item.get("doc_fat"),
                        "dados": item.get("dados"),
                        "cliente": contexto["cliente"],
                    }
                )

            self.logger.add(
                6,
                "F110 de Água e Esgoto concluídos. Selecionando boletos finais na SP02.",
                publico=True,
            )
            resultado_sp02 = selecionar_boletos_sp02(
                session,
                boletos_para_sp02,
                logger=self.logger,
                progress_callback=progress_callback,
                notice_callback=notice_callback,
                aguardar_apos_copia_segundos=7,
            )
            self._garantir_janela_unica_sap(session, origem="SP02 Água + Esgoto")

            for spool in resultado_sp02.get("spools_boletos") or []:
                item = itens_por_tipo.get(str(spool.get("tipo") or ""))

                if not item:
                    continue

                item.update(
                    {
                        "nome_pdf_sugerido": spool.get("nome_pdf_sugerido"),
                        "spool_boleto": spool.get("spool"),
                    }
                )

            contexto["pedido"] = " | ".join(
                f"{item['tipo_label']}: {item.get('pedido') or '--'}"
                for item in itens
            )
            contexto["doc_fat"] = " | ".join(
                f"{item['tipo_label']}: {item.get('doc_fat') or '--'}"
                for item in itens
            )
            contexto["faturamento"] = contexto["doc_fat"]
            contexto["boleto"] = "GERADO"
            contexto["identificacao_pagamento"] = " | ".join(
                f"{item['tipo_label']}: {item.get('identificacao_pagamento') or '--'}"
                for item in itens
            )
            contexto["identificacoes_pagamento"] = {
                item["tipo"]: item.get("identificacao_pagamento")
                for item in itens
            }
            contexto["nomes_pdf_sugeridos"] = {
                item["tipo"]: item.get("nome_pdf_sugerido")
                for item in itens
                if item.get("nome_pdf_sugerido")
            }
            contexto["spools_boletos"] = resultado_sp02.get("spools_boletos") or []
            contexto["agua_esgoto"] = itens

            return resultado_padrao(
                ok=True,
                etapa="F110",
                mensagem="Processo Água + Esgoto completo com sucesso.",
                dados=self._montar_dados_publicos(dados, contexto),
            )

        except Exception as exc:
            self.logger.add(-1, f"Erro no fluxo Água + Esgoto: {exc}", nivel="ERRO")
            etapa_falha = (
                etapa_atual
                if etapa_atual in STAGE_ORDER or etapa_atual == "CONEXAO"
                else "XD03"
            )
            etapa_progresso = etapa_falha if etapa_falha in STAGE_ORDER else "XD03"
            self._notificar_progresso(
                progress_callback,
                etapa_progresso,
                "erro",
                f"Falha no fluxo Água + Esgoto em {etapa_falha}.",
            )
            return self._falha(
                etapa=etapa_falha,
                mensagem="Erro ao executar o fluxo Água + Esgoto.",
                erro_tecnico=str(exc),
                dados=dados,
                contexto=contexto,
                resume_from=etapa_falha if etapa_falha in STAGE_ORDER else None,
                session=session,
            )

    # Executa o fluxo SAP real: conexao, XD03, VA01, VF01, FB03/VF02 e F110.
    def executar_fluxo(
        self,
        dados,
        progress_callback=None,
        notice_callback=None,
        resume_checkpoint=None,
        cancel_event=None,
    ):
        iniciar_em, contexto_checkpoint = self._normalizar_checkpoint(resume_checkpoint)
        contexto = {
            "cliente": contexto_checkpoint.get("cliente"),
            "nome_cliente": contexto_checkpoint.get("nome_cliente"),
            "pedido": contexto_checkpoint.get("pedido"),
            "pedido_agua": contexto_checkpoint.get("pedido_agua"),
            "pedido_esgoto": contexto_checkpoint.get("pedido_esgoto"),
            "faturamento": contexto_checkpoint.get("faturamento"),
            "doc_fat": contexto_checkpoint.get("doc_fat"),
            "doc_fat_agua": contexto_checkpoint.get("doc_fat_agua"),
            "doc_fat_esgoto": contexto_checkpoint.get("doc_fat_esgoto"),
            "boleto": contexto_checkpoint.get("boleto"),
            "identificacao_pagamento": contexto_checkpoint.get("identificacao_pagamento"),
            "identificacoes_pagamento": contexto_checkpoint.get("identificacoes_pagamento"),
            "agua_esgoto": contexto_checkpoint.get("agua_esgoto"),
        }

        if str(dados.get("tipo") or "").strip().lower() == TIPO_COMPOSTO_AGUA_ESGOTO:
            return self._executar_fluxo_agua_esgoto(
                dados,
                progress_callback=progress_callback,
                notice_callback=notice_callback,
                resume_checkpoint=resume_checkpoint,
                cancel_event=cancel_event,
            )

        session = None

        try:
            self.logger.add(-1, "Conectando ao SAP...", publico=True)
            self.logger.add(
                -1,
                f"Tipo de documento identificado: {dados['doc_info']['rotulo']}",
            )

            if iniciar_em != "XD03":
                self.logger.add(
                    -1,
                    f"Retomando fluxo a partir de {iniciar_em}.",
                    publico=True,
            )

            session = conectar_sap()
            self._garantir_janela_unica_sap(session, origem="conexão")

            cancelado = self._verificar_cancelamento(
                cancel_event,
                iniciar_em,
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            if iniciar_em != "XD03":
                self._sincronizar_progresso_retomada(progress_callback, iniciar_em)
                session = self._preparar_tela_para_retomada(
                    session,
                    iniciar_em,
                    progress_callback=progress_callback,
                )

        except Exception as e:
            self.logger.add(-1, f"Erro ao conectar ao SAP: {e}", nivel="ERRO")
            self._notificar_progresso(
                progress_callback,
                "CONEXAO",
                "erro",
                "Falha ao conectar ao SAP.",
            )
            return self._falha(
                etapa="CONEXAO",
                mensagem="Falha ao conectar ao SAP.",
                erro_tecnico=str(e),
                dados=dados,
                contexto=contexto,
                resume_from=iniciar_em if iniciar_em != "XD03" else None,
                session=session,
            )

        if self._deve_executar("XD03", iniciar_em):
            cancelado = self._verificar_cancelamento(
                cancel_event,
                "XD03",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            resultado_xd03 = buscar_cliente(
                session,
                dados,
                self.logger,
                progress_callback=progress_callback,
            )

            if not resultado_xd03["ok"]:
                self.logger.add(-1, "Falha na etapa XD03.", nivel="ERRO")
                return self._falha(
                    etapa="XD03",
                    mensagem=resultado_xd03["mensagem"],
                    erro_tecnico=resultado_xd03.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from="XD03",
                    session=session,
                )

            contexto["cliente"] = resultado_xd03["dados"]["cliente"]
            contexto["nome_cliente"] = resultado_xd03["dados"].get("nome_cliente")
            self.logger.add(
                0,
                f"Cliente validado: {contexto['cliente']}",
                publico=True,
            )
            self._garantir_janela_unica_sap(session, origem="XD03")

            cancelado = self._verificar_cancelamento(
                cancel_event,
                "VA01",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado
        elif not contexto.get("cliente"):
            return self._falha(
                etapa="XD03",
                mensagem="Não foi possível retomar o fluxo: cliente ausente no checkpoint.",
                erro_tecnico="Checkpoint sem cliente.",
                dados=dados,
                contexto=contexto,
                resume_from="XD03",
                session=session,
            )

        if self._deve_executar("VA01", iniciar_em):
            cancelado = self._verificar_cancelamento(
                cancel_event,
                "VA01",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            resultado_va01 = criar_pedido(
                session,
                dados,
                contexto["cliente"],
                self.logger,
                progress_callback=progress_callback,
            )

            if not resultado_va01["ok"]:
                self.logger.add(-1, "Falha na etapa VA01.", nivel="ERRO")
                return self._falha(
                    etapa="VA01",
                    mensagem=resultado_va01["mensagem"],
                    erro_tecnico=resultado_va01.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from="VA01",
                    session=session,
                )

            dados_va01 = resultado_va01.get("dados") or {}
            contexto["pedido"] = (
                dados_va01.get("pedido")
                or dados_va01.get("ordem")
                or _extrair_numero_sap(dados_va01.get("status_sap"))
                or contexto.get("pedido")
            )
            self._garantir_janela_unica_sap(session, origem="VA01")

            cancelado = self._verificar_cancelamento(
                cancel_event,
                "VF01",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

        if self._deve_executar("VF01", iniciar_em):
            cancelado = self._verificar_cancelamento(
                cancel_event,
                "VF01",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            resultado_vf01 = criar_doc_faturamento(
                session,
                self.logger,
                progress_callback=progress_callback,
            )

            if not resultado_vf01["ok"]:
                self.logger.add(-1, "Falha na etapa VF01.", nivel="ERRO")
                return self._falha(
                    etapa="VF01",
                    mensagem=resultado_vf01["mensagem"],
                    erro_tecnico=resultado_vf01.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from="VF01",
                    session=session,
                )

            contexto["faturamento"] = resultado_vf01["dados"]["faturamento"]
            contexto["doc_fat"] = (
                resultado_vf01["dados"].get("doc_fat")
                or resultado_vf01["dados"].get("faturamento")
                or contexto.get("doc_fat")
            )
            self._garantir_janela_unica_sap(session, origem="VF01")

            cancelado = self._verificar_cancelamento(
                cancel_event,
                "FB03",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado
        elif not contexto.get("faturamento"):
            return self._falha(
                etapa="VF01",
                mensagem="Não foi possível retomar o fluxo: faturamento ausente no checkpoint.",
                erro_tecnico="Checkpoint sem faturamento.",
                dados=dados,
                contexto=contexto,
                resume_from="VF01",
                session=session,
            )

        if self._deve_executar("FB03", iniciar_em):
            inicio_pos_faturamento = "FB03"
        elif self._deve_executar("VF02_RESALVAR", iniciar_em):
            inicio_pos_faturamento = "VF02_RESALVAR"
        else:
            inicio_pos_faturamento = None

        if inicio_pos_faturamento:
            cancelado = self._verificar_cancelamento(
                cancel_event,
                inicio_pos_faturamento,
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            resultado_vf02 = pos_faturamento(
                session,
                contexto["faturamento"],
                self.logger,
                progress_callback=progress_callback,
                start_from=inicio_pos_faturamento,
            )

            if not resultado_vf02["ok"]:
                contexto["faturamento"] = (
                    (resultado_vf02.get("dados") or {}).get("faturamento")
                    or contexto.get("faturamento")
                )

                return self._falha(
                    etapa=resultado_vf02.get("etapa") or "FB03",
                    mensagem=resultado_vf02["mensagem"],
                    erro_tecnico=resultado_vf02.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from=resultado_vf02.get("etapa") or "FB03",
                    session=session,
                )

            contexto["faturamento"] = resultado_vf02["dados"]["faturamento"]
            self._garantir_janela_unica_sap(session, origem="FB03/VF02")

            cancelado = self._verificar_cancelamento(
                cancel_event,
                "F110",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

        if self._deve_executar("F110", iniciar_em):
            cancelado = self._verificar_cancelamento(
                cancel_event,
                "F110",
                dados,
                contexto,
                progress_callback=progress_callback,
            )

            if cancelado:
                return cancelado

            if not contexto.get("cliente"):
                return self._falha(
                    etapa="F110",
                    mensagem="Não foi possível seguir para F110: cliente ausente.",
                    erro_tecnico="Contexto sem cliente.",
                    dados=dados,
                    contexto=contexto,
                    resume_from="F110",
                    session=session,
                )

            if not contexto.get("doc_fat"):
                return self._falha(
                    etapa="F110",
                    mensagem="Não foi possível seguir para F110: doc_fat ausente.",
                    erro_tecnico="Contexto sem doc_fat.",
                    dados=dados,
                    contexto=contexto,
                    resume_from="F110",
                    session=session,
                )

            dados_f110 = {
                **dados,
                "nome_cliente": contexto.get("nome_cliente"),
            }

            resultado_f110 = f110(
                session,
                contexto["cliente"],
                contexto["doc_fat"],
                self.logger,
                progress_callback=progress_callback,
                notice_callback=notice_callback,
                dados=dados_f110,
            )

            if not resultado_f110["ok"]:
                contexto["boleto"] = (
                    (resultado_f110.get("dados") or {}).get("boleto")
                    or contexto.get("boleto")
                )
                contexto["identificacao_pagamento"] = (
                    (resultado_f110.get("dados") or {}).get("identificacao_pagamento")
                    or contexto.get("identificacao_pagamento")
                )

                return self._falha(
                    etapa="F110",
                    mensagem=resultado_f110["mensagem"],
                    erro_tecnico=resultado_f110.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from="F110",
                    session=session,
                )

            contexto["boleto"] = (resultado_f110.get("dados") or {}).get("boleto")
            contexto["identificacao_pagamento"] = (
                (resultado_f110.get("dados") or {}).get("identificacao_pagamento")
            )
            self._garantir_janela_unica_sap(session, origem="F110")

        return resultado_padrao(
            ok=True,
            etapa="F110",
            mensagem="Processo completo com sucesso.",
            dados=self._montar_dados_publicos(dados, contexto),
        )
