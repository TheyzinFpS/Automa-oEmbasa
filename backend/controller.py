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

        self.logger.add(-1, f"Iniciando criação do pedido de {tipo_label}.", publico=True)

        cancelado = self._verificar_cancelamento(
            cancel_event,
            "VA01",
            dados_tipo,
            contexto,
            progress_callback=progress_callback,
        )

        if cancelado:
            return cancelado, None

        resultado_va01 = criar_pedido(
            session,
            dados_tipo,
            contexto["cliente"],
            self.logger,
            progress_callback=progress_callback,
        )

        if not resultado_va01["ok"]:
            return self._falha(
                etapa="VA01",
                mensagem=resultado_va01["mensagem"],
                erro_tecnico=resultado_va01.get("erro_tecnico"),
                dados=dados_tipo,
                contexto=contexto,
                resume_from="VA01",
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
            progress_callback=progress_callback,
        )

        if cancelado:
            return cancelado, None

        resultado_vf01 = criar_doc_faturamento(
            session,
            self.logger,
            progress_callback=progress_callback,
        )

        if not resultado_vf01["ok"]:
            return self._falha(
                etapa="VF01",
                mensagem=resultado_vf01["mensagem"],
                erro_tecnico=resultado_vf01.get("erro_tecnico"),
                dados=dados_tipo,
                contexto=contexto,
                resume_from="VF01",
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
            progress_callback=progress_callback,
        )

        if cancelado:
            return cancelado, None

        resultado_vf02 = pos_faturamento(
            session,
            faturamento,
            self.logger,
            progress_callback=progress_callback,
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

        try:
            self.logger.add(-1, "Conectando ao SAP...", publico=True)
            self.logger.add(-1, "Fluxo composto selecionado: Água + Esgoto.", publico=True)

            session = conectar_sap()
            self._garantir_janela_unica_sap(session, origem="conexão")

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

            for tipo in TIPOS_AGUA_ESGOTO:
                dados_tipo = self._dados_com_tipo(dados, tipo)
                falha, item = self._executar_criacao_ate_vf02(
                    session,
                    dados_tipo,
                    contexto,
                    cancel_event=cancel_event,
                    progress_callback=progress_callback,
                )

                if falha:
                    return falha

                itens.append(item)
                contexto[f"pedido_{tipo}"] = item.get("pedido")
                contexto[f"doc_fat_{tipo}"] = item.get("doc_fat")

            resultados_f110 = []

            for item in itens:
                cancelado = self._verificar_cancelamento(
                    cancel_event,
                    "F110",
                    item["dados"],
                    contexto,
                    progress_callback=progress_callback,
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
                    progress_callback=progress_callback,
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
                resultados_f110.append(dados_f110)

            finalizacao_sp02 = selecionar_boletos_sp02(
                session,
                [
                    {
                        "tipo": item["tipo"],
                        "doc_fat": item["doc_fat"],
                        "dados": item["dados"],
                        "cliente": contexto["cliente"],
                    }
                    for item in reversed(itens)
                ],
                logger=self.logger,
                progress_callback=progress_callback,
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
            contexto["agua_esgoto"] = itens
            contexto.update(finalizacao_sp02)

            return resultado_padrao(
                ok=True,
                etapa="F110",
                mensagem="Processo Água + Esgoto completo com sucesso.",
                dados=self._montar_dados_publicos(dados, contexto),
            )

        except Exception as exc:
            self.logger.add(-1, f"Erro no fluxo Água + Esgoto: {exc}", nivel="ERRO")
            self._notificar_progresso(
                progress_callback,
                "F110",
                "erro",
                "Falha no fluxo Água + Esgoto.",
            )
            return self._falha(
                etapa="F110",
                mensagem="Erro ao executar o fluxo Água + Esgoto.",
                erro_tecnico=str(exc),
                dados=dados,
                contexto=contexto,
                resume_from="F110",
            )

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
                resume_checkpoint=resume_checkpoint,
                cancel_event=cancel_event,
            )

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
