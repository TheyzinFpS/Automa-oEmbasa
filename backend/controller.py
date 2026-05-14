import json

from backend.flows.f110 import f110
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
            return session

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
            "faturamento": contexto.get("faturamento"),
            "doc_fat": contexto.get("doc_fat"),
            "boleto": contexto.get("boleto"),
            "identificacao_pagamento": contexto.get("identificacao_pagamento"),
            "documento": dados["doc"],
            "tipo_documento": dados["doc_info"]["rotulo"],
            "valor": dados["valor_info"]["formatado"],
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
            "contexto": self._montar_dados_publicos(dados, contexto),
        }

    # Centraliza resposta de erro e inclui checkpoint quando a etapa pode ser retomada.
    def _falha(
        self,
        etapa,
        mensagem,
        erro_tecnico,
        dados,
        contexto,
        resume_from=None,
    ):
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

    # Executa o fluxo SAP real: conexao, XD03, VA01, VF01, FB03/VF02 e F110.
    def executar_fluxo(
        self,
        dados,
        progress_callback=None,
        resume_checkpoint=None,
        cancel_event=None,
    ):
        iniciar_em, contexto_checkpoint = self._normalizar_checkpoint(resume_checkpoint)
        contexto = {
            "cliente": contexto_checkpoint.get("cliente"),
            "nome_cliente": contexto_checkpoint.get("nome_cliente"),
            "faturamento": contexto_checkpoint.get("faturamento"),
            "doc_fat": contexto_checkpoint.get("doc_fat"),
            "boleto": contexto_checkpoint.get("boleto"),
            "identificacao_pagamento": contexto_checkpoint.get("identificacao_pagamento"),
        }

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
                )

            if not contexto.get("doc_fat"):
                return self._falha(
                    etapa="F110",
                    mensagem="Não foi possível seguir para F110: doc_fat ausente.",
                    erro_tecnico="Contexto sem doc_fat.",
                    dados=dados,
                    contexto=contexto,
                    resume_from="F110",
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
