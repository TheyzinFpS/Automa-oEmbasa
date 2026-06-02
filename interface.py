from __future__ import annotations

import json
import threading
import time
import traceback
from pathlib import Path

import webview

from backend.controller import SAPController
from backend.documentos import analisar_doc, limpar_doc
from backend.flows.cliente_cadastro import adicionar_setores_cliente, criar_cliente
from backend.history import (
    diagnostico_historico,
    listar_historico_pedidos,
    obter_historico_pedido,
    registrar_historico_pedido,
)
from backend.logger import Logger
from backend.sap_connection import conectar_sap
from backend.utils.sap_waits import SapKeepAlive
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
        self._sap_activity_lock = threading.Lock()
        self._flow_running = False
        self._cancel_event = threading.Event()
        self._last_progress = {}
        self._notice_lock = threading.Lock()
        self._notice_events = {}
        self._keep_alive = SapKeepAlive(
            intervalo=60,
            pode_executar=self._pode_executar_keep_alive,
            bloqueio_atividade=self._sap_activity_lock,
        )
        self._keep_alive.start()

    def set_window(self, window):
        self._window = window

    def stop(self):
        self._keep_alive.stop()

    def _pode_executar_keep_alive(self):
        with self._flow_lock:
            return not self._flow_running

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
                run_js = getattr(window, "run_js", None)

                if callable(run_js):
                    run_js(script)
                else:
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
        mensagem_texto = "" if mensagem is None else str(mensagem)

        if mensagem_texto.startswith("PDF_NAME_READY::"):
            self._trazer_interface_para_frente(maximizar=True)

        self._last_progress = {
            "etapa": str(etapa or ""),
            "status": str(status or ""),
            "mensagem": mensagem_texto,
            "percentual": percentual,
        }

        self._emitir_funcao_js(
            "atualizarProgresso",
            self._last_progress,
        )

    def _trazer_interface_para_frente(self, maximizar=False):
        window = self._get_window()

        if window is None:
            return

        for method_name in ("restore", "show"):
            method = getattr(window, method_name, None)

            if not callable(method):
                continue

            try:
                method()
            except Exception:
                continue

        if maximizar:
            method = getattr(window, "maximize", None)

            if callable(method):
                try:
                    method()
                except Exception:
                    pass

        try:
            window.on_top = True
            time.sleep(0.12)
            window.on_top = False
        except Exception:
            pass

        self._evaluate_js_safe("try { window.focus(); } catch (e) {}")

    def _aguardar_aviso_operacional(self, tipo, payload=None, timeout=900):
        """
        Aviso operacional apenas informativo.

        Não aguarda clique, confirmação nem retorno do frontend.
        Isso evita travamento do pywebview quando o fluxo SAP já terminou
        ou quando o backend está ocupado.
        """

        payload = dict(payload or {})
        payload["tipo"] = str(tipo or "")

        self._emitir_funcao_js(
            "mostrarAvisoOperacional",
            str(tipo or ""),
            _serializar_para_front(payload),
        )

        return True

    # Encaminha logs publicos do backend para o balao de logs em tempo real.
    def _instalar_logger_tempo_real(self):
        logger = self._logger
        add_original = logger.add
        api = self

        def add_interceptado(etapa, msg, nivel="INFO", publico=False):
            add_original(etapa, msg, nivel=nivel, publico=publico)

            if publico:
                classe = "error" if str(nivel).upper() == "ERRO" else ""
                mensagem_publica = msg

                try:
                    if logger.public_logs:
                        mensagem_publica = logger.public_logs[-1]["msg"]
                except Exception:
                    mensagem_publica = msg

                api._emitir_log(mensagem_publica, classe)

        logger.add = add_interceptado
        return add_original

    def _restaurar_logger(self, add_original):
        self._logger.add = add_original

    def _executar_fluxo_com_callback(self, dados_tratados, resume_checkpoint=None):
        return self._controller.executar_fluxo(
            dados_tratados,
            progress_callback=self._emitir_progresso,
            notice_callback=self._aguardar_aviso_operacional,
            resume_checkpoint=resume_checkpoint,
            cancel_event=self._cancel_event,
        )

    def confirmar_aviso_operacional(self, notice_id):
        with self._notice_lock:
            evento = self._notice_events.get(str(notice_id or ""))

        if evento is None:
            return {"ok": False, "msg": "Aviso operacional não encontrado."}

        evento.set()
        return {"ok": True}

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

                with self._sap_activity_lock:
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
                            else (
                                f"Resumo da falha: etapa {resultado['etapa']} - "
                                f"{resultado['mensagem']}. Veja o diagnóstico detalhado acima."
                            )
                        ),
                        nivel="ERRO",
                        publico=cancelado,
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
                                "acao_pendente": resultado.get("acao_pendente"),
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

                dados_resultado = resultado.get("dados") or {}
                resultado["dados"] = dados_resultado

                registro_historico = registrar_historico_pedido(
                    dados_tratados,
                    dados_resultado,
                    logger=self._logger,
                )

                if registro_historico:
                    dados_resultado["historico_id"] = registro_historico.get("id")
                    dados_resultado["historico_txt"] = registro_historico.get("txt_path")

                payload_sucesso = {
                    "ok": True,
                    "logs": self._logger.get_logs(public_only=True),
                    "resultado": dados_resultado,
                    "doc_info": dados_tratados["doc_info"],
                    "valor_info": dados_tratados["valor_info"],
                    "checkpoint": None,
                    "tempo_real": True,
                }

                resultado_final.update(_serializar_para_front(payload_sucesso))
                self._emitir_preencher_resultado(resultado["dados"] or {})
                self._emitir_status("Concluído", "success")

            except Exception as e:
                erro_publico = (
                    "Falha detalhada fora de uma etapa SAP.\n"
                    "O que o sistema fazia: preparar, executar ou finalizar a chamada entre interface e backend.\n"
                    f"Bloqueio técnico retornado: {str(e) or 'sem detalhe retornado'}.\n"
                    f"Log técnico completo: {self._logger.log_file_path}."
                )
                self._logger.add(
                    -1,
                    erro_publico,
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

    def _executar_acao_cliente_sap(self, dados, executor, status_texto):
        resultado_final = {}
        concluido = threading.Event()

        with self._flow_lock:
            if self._flow_running:
                return {
                    "ok": False,
                    "msg": "Ja existe uma acao SAP em andamento.",
                    "tempo_real": True,
                }

            self._flow_running = True
            self._cancel_event.clear()

        def worker():
            add_original = self._instalar_logger_tempo_real()

            try:
                self._emitir_status(status_texto, "running")
                self._logger.add(-1, status_texto, publico=True)
                with self._sap_activity_lock:
                    session = conectar_sap()
                    resultado = executor(
                        session,
                        dados,
                        self._logger,
                        progress_callback=self._emitir_progresso,
                    )
                resultado = _serializar_para_front(resultado)

                payload = {
                    "ok": bool(resultado.get("ok")),
                    "msg": resultado.get("mensagem") or "",
                    "resultado": resultado.get("dados") or {},
                    "logs": self._logger.get_logs(public_only=True),
                    "tempo_real": True,
                }

                resultado_final.update(_serializar_para_front(payload))

                if payload["ok"]:
                    self._emitir_status("Concluido", "success")
                else:
                    self._emitir_status("Falha no processamento", "error")
            except Exception as exc:
                self._logger.add(
                    -1,
                    f"Falha na acao de cadastro SAP: {exc}",
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
                        "msg": "Erro inesperado na acao de cadastro SAP.",
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

    def cadastrar_cliente_sap(self, dados):
        return self._executar_acao_cliente_sap(
            dados,
            criar_cliente,
            "Cadastrando cliente no SAP",
        )

    def adicionar_setores_cliente_sap(self, dados):
        return self._executar_acao_cliente_sap(
            dados,
            adicionar_setores_cliente,
            "Cadastrando setores no SAP",
        )

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
                "msg": (
                    "Seu pedido foi enviado com sucesso para o atendimento interno. "
                    f"Protocolo: {resultado['protocolo']}."
                ),
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
                "history": diagnostico_historico(),
                "log_file": self._logger.log_file_path,
            }
        )

    # Lista registros gravados no historico compartilhado/local.
    def listar_historico(self, filtro="", limite=None):
        try:
            return _serializar_para_front(
                {
                    "ok": True,
                    "itens": listar_historico_pedidos(filtro=filtro, limite=limite),
                }
            )
        except Exception as exc:
            return {
                "ok": False,
                "msg": f"Falha ao carregar histórico: {exc}",
                "itens": [],
            }

    # Retorna o detalhe completo de um registro de historico.
    def obter_historico(self, registro_id):
        try:
            registro = obter_historico_pedido(registro_id)
        except Exception as exc:
            return {
                "ok": False,
                "msg": f"Falha ao abrir histórico: {exc}",
            }

        if not registro:
            return {
                "ok": False,
                "msg": "Registro de histórico não encontrado.",
            }

        return _serializar_para_front(
            {
                "ok": True,
                "registro": registro,
            }
        )
