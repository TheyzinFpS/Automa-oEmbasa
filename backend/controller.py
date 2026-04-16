from backend.flows.common import resultado_padrao
from backend.flows.f110 import f110
from backend.flows.va01 import criar_pedido
from backend.flows.vf01 import criar_doc_faturamento
from backend.flows.vf02 import pos_faturamento
from backend.flows.xd03 import buscar_cliente
from backend.sap_connection import conectar_sap


ENABLE_F110_NO_FLUXO = False
FORCAR_TESTE_ISOLADO_F110 = False
TESTE_F110_CONTEXTO = {
    "cliente": "",
    "doc_fat": "",
    "faturamento": "",
}


STAGE_ORDER = [
    "XD03",
    "VA01",
    "VF01",
    "VF02_CAPTURA",
    "FB03",
    "VF02_RESALVAR",
    "F110",
]
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGE_ORDER)}
CONTEXTO_CHAVES = (
    "cliente",
    "faturamento",
    "doc_fat",
    "boleto",
    "identificacao_pagamento",
)
class SAPController:
    def __init__(self, logger):
        self.logger = logger

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

    def _indice_etapa(self, etapa):
        return STAGE_INDEX.get(str(etapa or "").strip().upper(), -1)

    def _deve_executar(self, etapa, iniciar_em):
        indice_etapa = self._indice_etapa(etapa)
        indice_inicio = self._indice_etapa(iniciar_em)

        if indice_etapa == -1 or indice_inicio == -1:
            return True

        return indice_etapa >= indice_inicio

    def _normalizar_checkpoint(self, checkpoint):
        if not isinstance(checkpoint, dict):
            return "XD03", {}

        iniciar_em = str(checkpoint.get("resume_from") or "XD03").strip().upper()
        contexto = dict(checkpoint.get("contexto") or {})

        if self._indice_etapa(iniciar_em) == -1:
            iniciar_em = "XD03"

        return iniciar_em, contexto

    def _criar_contexto(self, contexto_checkpoint):
        return {
            chave: contexto_checkpoint.get(chave)
            for chave in CONTEXTO_CHAVES
        }

    def _falha_checkpoint_ausente(self, etapa, campo, dados, contexto):
        return self._falha(
            etapa=etapa,
            mensagem=(
                f"Nao foi possivel retomar o fluxo: {campo} ausente no checkpoint."
            ),
            erro_tecnico=f"Checkpoint sem {campo}.",
            dados=dados,
            contexto=contexto,
            resume_from=etapa,
        )

    def _montar_dados_publicos(self, dados, contexto):
        retorno = {
            "cliente": contexto.get("cliente"),
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

    def _montar_checkpoint(self, resume_from, dados, contexto):
        return {
            "resume_from": resume_from,
            "contexto": self._montar_dados_publicos(dados, contexto),
        }

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

    def executar_fluxo(self, dados, progress_callback=None, resume_checkpoint=None):
        iniciar_em, contexto_checkpoint = self._normalizar_checkpoint(resume_checkpoint)

        if FORCAR_TESTE_ISOLADO_F110:
            iniciar_em = "F110"
            contexto_checkpoint = {
                **contexto_checkpoint,
                **TESTE_F110_CONTEXTO,
            }

        contexto = self._criar_contexto(contexto_checkpoint)

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
            self.logger.add(
                0,
                f"Cliente validado: {contexto['cliente']}",
                publico=True,
            )
        elif not contexto.get("cliente"):
            return self._falha_checkpoint_ausente("XD03", "cliente", dados, contexto)

        if self._deve_executar("VA01", iniciar_em):
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

        if self._deve_executar("VF01", iniciar_em):
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
        elif iniciar_em != "F110" and not contexto.get("faturamento"):
            return self._falha_checkpoint_ausente(
                "VF01",
                "faturamento",
                dados,
                contexto,
            )

        if self._deve_executar("VF02_CAPTURA", iniciar_em):
            inicio_pos_faturamento = "VF02_CAPTURA"
        elif self._deve_executar("FB03", iniciar_em):
            inicio_pos_faturamento = "FB03"
        elif self._deve_executar("VF02_RESALVAR", iniciar_em):
            inicio_pos_faturamento = "VF02_RESALVAR"
        else:
            inicio_pos_faturamento = None

        if inicio_pos_faturamento:
            resultado_vf02 = pos_faturamento(
                session,
                contexto["faturamento"],
                self.logger,
                progress_callback=progress_callback,
                start_from=inicio_pos_faturamento,
                existing_doc_fat=contexto.get("doc_fat"),
            )

            if not resultado_vf02["ok"]:
                contexto["doc_fat"] = (
                    (resultado_vf02.get("dados") or {}).get("doc_fat")
                    or contexto.get("doc_fat")
                )
                contexto["faturamento"] = (
                    (resultado_vf02.get("dados") or {}).get("faturamento")
                    or contexto.get("faturamento")
                )

                return self._falha(
                    etapa=resultado_vf02.get("etapa") or "VF02_CAPTURA",
                    mensagem=resultado_vf02["mensagem"],
                    erro_tecnico=resultado_vf02.get("erro_tecnico"),
                    dados=dados,
                    contexto=contexto,
                    resume_from=resultado_vf02.get("etapa") or "VF02_CAPTURA",
                )

            contexto["doc_fat"] = resultado_vf02["dados"]["doc_fat"]
            contexto["faturamento"] = resultado_vf02["dados"]["faturamento"]
        elif iniciar_em != "F110" and not contexto.get("doc_fat"):
            return self._falha_checkpoint_ausente(
                "VF02_CAPTURA",
                "doc_fat",
                dados,
                contexto,
            )

        if not ENABLE_F110_NO_FLUXO:
            self.logger.add(
                6,
                "F110 mantido em modo mockado e fora do fluxo principal nesta versao.",
            )

            return resultado_padrao(
                ok=True,
                etapa="VF02_RESALVAR",
                mensagem=(
                    "Fluxo executado com sucesso ate o re-salvamento do faturamento. "
                    "F110 permanece desativado no fluxo principal."
                ),
                dados=self._montar_dados_publicos(dados, contexto),
            )

        if self._deve_executar("F110", iniciar_em):
            resultado_f110 = f110(
                session,
                contexto["cliente"],
                contexto["doc_fat"],
                self.logger,
                progress_callback=progress_callback,
            )

            if not resultado_f110["ok"]:
                contexto["boleto"] = (
                    (resultado_f110.get("dados") or {}).get("boleto")
                    or contexto.get("boleto")
                )
                contexto["identificacao_pagamento"] = (
                    (resultado_f110.get("dados") or {}).get(
                        "identificacao_pagamento"
                    )
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

            contexto["boleto"] = resultado_f110["dados"].get("boleto")
            contexto["identificacao_pagamento"] = resultado_f110["dados"].get(
                "identificacao_pagamento"
            )

        return resultado_padrao(
            ok=True,
            etapa="F110",
            mensagem="Processo completo com sucesso.",
            dados=self._montar_dados_publicos(dados, contexto),
        )
