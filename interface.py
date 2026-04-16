from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime

import webview

from backend.controller import SAPController
from backend.documentos import analisar_doc, limpar_doc
from backend.logger import Logger
from backend.settings import SETTINGS
from backend.validators import validar_dados
from backend.valores import analisar_valor


class API:
    def __init__(self):
        self.logger = Logger()
        self.controller = SAPController(self.logger)
        self._window = None
        self._ui_lock = threading.Lock()

    def set_window(self, window):
        self._window = window

    def _get_window(self):
        if self._window is not None:
            return self._window

        try:
            if webview.windows:
                self._window = webview.windows[0]
                return self._window
        except Exception:
            return None

        return None

    def _evaluate_js_safe(self, script: str) -> bool:
        window = self._get_window()

        if window is None:
            return False

        try:
            with self._ui_lock:
                window.evaluate_js(script)
            return True
        except Exception:
            return False

    def _emitir_reset_progresso(self):
        self._emitir_funcao_js("resetarProgresso")

    def _emitir_funcao_js(self, nome_funcao: str, *args) -> bool:
        payload_nome = json.dumps(str(nome_funcao or ""))
        payload_args = ", ".join(
            json.dumps(arg, ensure_ascii=False)
            for arg in args
        )

        return self._evaluate_js_safe(
            f"""
            try {{
              const fn = window[{payload_nome}];
              if (typeof fn === "function") {{
                fn({payload_args});
              }}
            }} catch (e) {{}}
            """
        )

    def _emitir_log(self, mensagem: str, classe: str = ""):
        self._emitir_funcao_js("log", str(mensagem or ""), str(classe or ""))

    def _emitir_status(self, texto: str, classe: str):
        self._emitir_funcao_js("setStatus", str(texto or ""), str(classe or ""))

    def _emitir_preencher_resultado(self, resultado: dict):
        self._emitir_funcao_js("preencherResultado", resultado or {})

    def _emitir_progresso(
        self,
        etapa: str,
        status: str,
        mensagem: str | None = None,
        percentual: int | float | None = None,
    ):
        self._emitir_funcao_js(
            "atualizarProgresso",
            {
                "etapa": str(etapa or ""),
                "status": str(status or ""),
                "mensagem": "" if mensagem is None else str(mensagem),
                "percentual": percentual,
            },
        )

    def _instalar_logger_tempo_real(self):
        logger = self.logger
        add_original = logger.add
        api = self

        def add_interceptado(etapa, msg, nivel="INFO", publico=False):
            add_original(etapa, msg, nivel=nivel, publico=publico)

            if publico:
                classe = "error" if str(nivel).upper() == "ERRO" else ""
                api._emitir_log(msg, classe)

        logger.add = add_interceptado
        return add_original

    def _restaurar_logger(self, add_original):
        self.logger.add = add_original

    def _executar_fluxo_com_callback(self, dados_tratados, resume_checkpoint=None):
        return self.controller.executar_fluxo(
            dados_tratados,
            progress_callback=self._emitir_progresso,
            resume_checkpoint=resume_checkpoint,
        )

    def gerar_boleto(self, dados):
        resultado_final = {}
        concluido = threading.Event()

        def worker():
            add_original = self._instalar_logger_tempo_real()

            try:
                dados_tratados = dict(dados)
                resume_checkpoint = dados_tratados.get("_resume_checkpoint")
                resume_mode = isinstance(resume_checkpoint, dict) and bool(
                    resume_checkpoint
                )

                if not resume_mode:
                    self.logger.clear()
                    self._emitir_reset_progresso()
                    self._emitir_status("Processando", "running")
                else:
                    self._emitir_status("Retomando", "running")

                dados_tratados["doc"] = limpar_doc(dados.get("doc", ""))[:14]
                dados_tratados["doc_info"] = analisar_doc(dados_tratados["doc"])
                dados_tratados["modo_valor"] = dados.get("modo_valor", "auto")

                erros = validar_dados(dados_tratados)

                if erros:
                    resultado_final.update(
                        {
                            "ok": False,
                            "msg": "Erros: " + ", ".join(erros),
                            "doc_info": dados_tratados["doc_info"],
                            "tempo_real": True,
                        }
                    )
                    self._emitir_status("Atencao", "error")
                    return

                dados_tratados["valor_info"] = analisar_valor(dados.get("valor", ""))
                dados_tratados["valor"] = dados_tratados["valor_info"]["formatado"]

                self.logger.add(
                    -1,
                    f"Documento preparado para SAP: {dados_tratados['doc']}",
                    publico=False,
                )
                self.logger.add(
                    -1,
                    f"Valor confirmado: {dados_tratados['valor_info']['formatado']}",
                    publico=False,
                )

                resultado = self._executar_fluxo_com_callback(
                    dados_tratados,
                    resume_checkpoint=resume_checkpoint,
                )

                if not resultado["ok"]:
                    self.logger.add(
                        -1,
                        f"Falha na etapa {resultado['etapa']}: {resultado['mensagem']}",
                        nivel="ERRO",
                        publico=True,
                    )

                    if resultado.get("dados"):
                        self._emitir_preencher_resultado(resultado["dados"] or {})

                    resultado_final.update(
                        {
                            "ok": False,
                            "msg": resultado["mensagem"],
                            "logs": self.logger.get_logs(public_only=True),
                            "doc_info": dados_tratados["doc_info"],
                            "resultado": resultado.get("dados") or {},
                            "checkpoint": resultado.get("checkpoint"),
                            "tempo_real": True,
                        }
                    )

                    self._emitir_status("Falha no processamento", "error")
                    return

                payload_sucesso = {
                    "ok": True,
                    "logs": self.logger.get_logs(public_only=True),
                    "resultado": resultado["dados"],
                    "doc_info": dados_tratados["doc_info"],
                    "valor_info": dados_tratados["valor_info"],
                    "checkpoint": None,
                    "tempo_real": True,
                }

                resultado_final.update(payload_sucesso)
                self._emitir_preencher_resultado(resultado["dados"] or {})
                self._emitir_status("Concluido", "success")

            except Exception as e:
                self.logger.add(
                    -1,
                    f"Erro inesperado: {str(e)}",
                    nivel="ERRO",
                    publico=True,
                )
                self.logger.add(
                    -1,
                    traceback.format_exc(),
                    nivel="DEBUG",
                    publico=False,
                )

                resultado_final.update(
                    {
                        "ok": False,
                        "msg": "Erro inesperado no processamento.",
                        "logs": self.logger.get_logs(public_only=True),
                        "tempo_real": True,
                    }
                )
                self._emitir_status("Falha no processamento", "error")

            finally:
                self._restaurar_logger(add_original)
                concluido.set()

        threading.Thread(target=worker, daemon=True).start()
        concluido.wait()

        return resultado_final

    def enviar_atendimento(self, dados):
        matricula = str(dados.get("matricula", "")).strip()
        nome = str(dados.get("nome", "")).strip()
        lotacao = str(dados.get("lotacao", "")).strip()
        setor = str(dados.get("setor", "")).strip()
        descricao = str(dados.get("descricao", "")).strip()
        imagens = dados.get("imagens", [])

        if not matricula:
            return {"ok": False, "msg": "Informe a matricula."}

        if not nome:
            return {"ok": False, "msg": "Informe o nome."}

        if not lotacao:
            return {"ok": False, "msg": "Informe a lotacao."}

        if not setor:
            return {"ok": False, "msg": "Informe o setor."}

        if not descricao:
            return {"ok": False, "msg": "Informe a descricao do atendimento."}

        if len(descricao) > 600:
            return {
                "ok": False,
                "msg": "A descricao deve ter no maximo 600 caracteres.",
            }

        protocolo = datetime.now().strftime("FAFTA-%Y%m%d-%H%M%S")

        return {
            "ok": True,
            "msg": "Pedido de Atendimento Enviado Com Sucesso",
            "protocolo": protocolo,
            "imagens_recebidas": len(imagens),
        }

    def obter_diagnostico(self):
        from backend.flows.xd03 import cache_cliente

        return {
            "ok": True,
            "app": SETTINGS.get("app", {}),
            "runtime": SETTINGS.get("_meta", {}),
            "cache": cache_cliente.stats(),
            "log_file": str(self.logger.log_file_path),
        }
