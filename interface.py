from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path

import webview

from backend.controller import SAPController
from backend.documentos import analisar_doc, limpar_doc
from backend.logger import Logger
from backend.support_mail import process_support_request
from backend.settings import SETTINGS
from backend.validators import validar_dados
from backend.valores import analisar_valor


# Converte objetos Python para tipos seguros de enviar ao JavaScript.
def _serializar_para_front(valor):
    if isinstance(valor, Path):
        return str(valor)

    if isinstance(valor, dict):
        return {
            str(chave): _serializar_para_front(conteudo)
            for chave, conteudo in valor.items()
        }

    if isinstance(valor, (list, tuple, set)):
        return [_serializar_para_front(item) for item in valor]

    return valor


# API exposta ao frontend pelo pywebview: o JS chama estes metodos.
class API:
    def __init__(self):
        self._logger = Logger()
        self._controller = SAPController(self._logger)
        self._window = None
        self._ui_lock = threading.Lock()
        self._flow_lock = threading.Lock()
        self._flow_running = False
        self._cancel_event = threading.Event()
        self._last_progress = {}

    def set_window(self, window):
        self._window = window

    # Localiza a janela ativa do pywebview para emitir eventos ao frontend.
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

    # Executa JavaScript na tela sem derrubar o backend caso a UI esteja indisponível.
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
            json.dumps(_serializar_para_front(arg), ensure_ascii=False)
            for arg in args
        )

        script = (
            "try {\n"
            f"  const fn = window[{payload_nome}];\n"
            '  if (typeof fn === "function") {\n'
            f"    fn({payload_args});\n"
            "  }\n"
            "} catch (e) {}\n"
        )

        return self._evaluate_js_safe(script)

    def _emitir_log(self, mensagem: str, classe: str = ""):
        self._emitir_funcao_js("log", str(mensagem or ""), str(classe or ""))

    def _emitir_status(self, texto: str, classe: str):
        self._emitir_funcao_js("setStatus", str(texto or ""), str(classe or ""))

    def _emitir_preencher_resultado(self, resultado: dict):
        self._emitir_funcao_js(
            "preencherResultado",
            _serializar_para_front(resultado or {}),
        )

    def _emitir_progresso(
        self,
        etapa: str,
        status: str,
        mensagem: str | None = None,
        percentual: int | float | None = None,
    ):
        self._last_progress = {
            "etapa": str(etapa or ""),
            "status": str(status or ""),
            "mensagem": "" if mensagem is None else str(mensagem),
            "percentual": percentual,
        }

        self._emitir_funcao_js(
            "atualizarProgresso",
            self._last_progress,
        )

    # Encaminha logs publicos do backend para o balao de logs em tempo real.
    def _instalar_logger_tempo_real(self):
        logger = self._logger
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
        self._logger.add = add_original

    def _executar_fluxo_com_callback(self, dados_tratados, resume_checkpoint=None):
        return self._controller.executar_fluxo(
            dados_tratados,
            progress_callback=self._emitir_progresso,
            resume_checkpoint=resume_checkpoint,
            cancel_event=self._cancel_event,
        )

    # Entrada principal chamada pelo botao Gerar Boleto.
    def gerar_boleto(self, dados):
        resultado_final = {}
        concluido = threading.Event()

        with self._flow_lock:
            if self._flow_running:
                return {
                    "ok": False,
                    "msg": "Já existe uma criação de boleto em andamento.",
                    "tempo_real": True,
                }

            self._flow_running = True
            self._cancel_event.clear()
            self._last_progress = {}

        def worker():
            add_original = self._instalar_logger_tempo_real()

            try:
                dados_tratados = dict(dados)
                resume_checkpoint = dados_tratados.get("_resume_checkpoint")
                resume_mode = isinstance(resume_checkpoint, dict) and bool(
                    resume_checkpoint
                )

                if not resume_mode:
                    self._logger.clear()
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
                        _serializar_para_front(
                            {
                                "ok": False,
                                "msg": "Erros: " + ", ".join(erros),
                                "doc_info": dados_tratados["doc_info"],
                                "tempo_real": True,
                            }
                        )
                    )
                    self._emitir_status("Atenção", "error")
                    return

                dados_tratados["valor_info"] = analisar_valor(dados.get("valor", ""))
                dados_tratados["valor"] = dados_tratados["valor_info"]["formatado"]

                self._logger.add(
                    -1,
                    f"Documento preparado para SAP: {dados_tratados['doc']}",
                    publico=False,
                )
                self._logger.add(
                    -1,
                    f"Valor confirmado: {dados_tratados['valor_info']['formatado']}",
                    publico=False,
                )

                resultado = self._executar_fluxo_com_callback(
                    dados_tratados,
                    resume_checkpoint=resume_checkpoint,
                )
                resultado = _serializar_para_front(resultado)

                if not resultado["ok"]:
                    cancelado = bool(resultado.get("cancelado"))
                    self._logger.add(
                        -1,
                        (
                            f"Cancelamento na etapa {resultado['etapa']}: {resultado['mensagem']}"
                            if cancelado
                            else f"Falha na etapa {resultado['etapa']}: {resultado['mensagem']}"
                        ),
                        nivel="ERRO",
                        publico=True,
                    )

                    if resultado.get("dados"):
                        self._emitir_preencher_resultado(resultado["dados"] or {})

                    resultado_final.update(
                        _serializar_para_front(
                            {
                                "ok": False,
                                "cancelado": cancelado,
                                "msg": resultado["mensagem"],
                                "logs": self._logger.get_logs(public_only=True),
                                "doc_info": dados_tratados["doc_info"],
                                "resultado": resultado.get("dados") or {},
                                "checkpoint": resultado.get("checkpoint"),
                                "tempo_real": True,
                            }
                        )
                    )

                    self._emitir_status(
                        "Cancelado" if cancelado else "Falha no processamento",
                        "error",
                    )
                    return

                payload_sucesso = {
                    "ok": True,
                    "logs": self._logger.get_logs(public_only=True),
                    "resultado": resultado["dados"],
                    "doc_info": dados_tratados["doc_info"],
                    "valor_info": dados_tratados["valor_info"],
                    "checkpoint": None,
                    "tempo_real": True,
                }

                resultado_final.update(_serializar_para_front(payload_sucesso))
                self._emitir_preencher_resultado(resultado["dados"] or {})
                self._emitir_status("Concluído", "success")

            except Exception as e:
                self._logger.add(
                    -1,
                    f"Erro inesperado: {str(e)}",
                    nivel="ERRO",
                    publico=True,
                )
                self._logger.add(
                    -1,
                    traceback.format_exc(),
                    nivel="DEBUG",
                    publico=False,
                )

                resultado_final.update(
                    {
                        "ok": False,
                        "msg": "Erro inesperado no processamento.",
                        "logs": _serializar_para_front(
                            self._logger.get_logs(public_only=True)
                        ),
                        "tempo_real": True,
                    }
                )
                self._emitir_status("Falha no processamento", "error")

            finally:
                self._restaurar_logger(add_original)
                with self._flow_lock:
                    self._flow_running = False
                concluido.set()

        threading.Thread(target=worker, daemon=True).start()
        concluido.wait()

        return _serializar_para_front(resultado_final)

    # Solicita parada no proximo ponto seguro do fluxo SAP em execucao.
    def cancelar_fluxo(self):
        with self._flow_lock:
            if not self._flow_running:
                return {
                    "ok": False,
                    "msg": "Nenhuma criação de boleto em andamento.",
                }

            self._cancel_event.set()

        ultima_etapa = self._last_progress.get("etapa") or "etapa ainda não informada"
        ultima_msg = self._last_progress.get("mensagem") or "aguardando próximo ponto seguro"
        mensagem = (
            "Cancelamento solicitado. O processo será interrompido no próximo ponto seguro. "
            f"Última etapa informada: {ultima_etapa}. Status: {ultima_msg}."
        )

        self._logger.add(-1, mensagem, nivel="ERRO", publico=True)
        self._emitir_log(mensagem, "error")
        self._emitir_status("Cancelando", "error")

        return {
            "ok": True,
            "msg": mensagem,
            "ultima_etapa": ultima_etapa,
            "ultima_mensagem": ultima_msg,
        }

    # Recebe os dados do Fale Conosco e delega validação/envio ao backend.
    def enviar_atendimento(self, dados):
        try:
            resultado = process_support_request(dados)
        except ValueError as exc:
            return {"ok": False, "msg": str(exc)}
        except Exception:
            self._logger.add(
                -1,
                traceback.format_exc(),
                nivel="DEBUG",
                publico=False,
            )
            return {
                "ok": False,
                "msg": "Falha ao registrar o pedido de atendimento.",
            }

        return _serializar_para_front(
            {
                "ok": True,
                "msg": "Seu pedido foi enviado com sucesso para o atendimento interno.",
                "protocolo": resultado["protocolo"],
                "snapshot_path": resultado["snapshot_path"],
                "email_destino": resultado.get("destination_email"),
            }
        )

    # Retorna informações técnicas usadas para diagnóstico local.
    def obter_diagnostico(self):
        from backend.flows.xd03 import cache_cliente

        return _serializar_para_front(
            {
                "ok": True,
                "app": SETTINGS.get("app", {}),
                "runtime": SETTINGS.get("_meta", {}),
                "cache": cache_cliente.stats(),
                "log_file": self._logger.log_file_path,
            }
        )
