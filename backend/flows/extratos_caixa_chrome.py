from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import websocket
except Exception:  # pragma: no cover - tratado em runtime no executavel.
    websocket = None


CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
CDP_BASE_URL = f"http://{CDP_HOST}:{CDP_PORT}"
CAIXA_EXTRATO_PATH = "/empresa/dashboard/govconta/selecao-govconta/extrato-individualizado"
CAIXA_EXTRATO_URL = f"https://gerenciador.caixa.gov.br{CAIXA_EXTRATO_PATH}"

MESES_SITE = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Marco",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro",
}

MESES_SIGLA = {
    "01": "JAN",
    "02": "FEV",
    "03": "MAR",
    "04": "ABR",
    "05": "MAI",
    "06": "JUN",
    "07": "JUL",
    "08": "AGO",
    "09": "SET",
    "10": "OUT",
    "11": "NOV",
    "12": "DEZ",
}


class CaixaChromeError(RuntimeError):
    pass


def _get_json(path: str, timeout: float = 3.0):
    url = f"{CDP_BASE_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _friendly_cdp_error(exc: Exception) -> str:
    if websocket is None:
        return (
            "Dependencia websocket-client ausente. Rode o rebuild para embutir "
            "a ponte de controle do Chrome."
        )

    if isinstance(exc, urllib.error.URLError):
        return (
            "Chrome controlavel nao encontrado na porta 9222. Abra o Chrome pelo "
            "arquivo Abrir_Chrome_Caixa_Controlavel.cmd, faca login na Caixa e tente novamente."
        )

    return str(exc) or exc.__class__.__name__


def diagnosticar_chrome_caixa() -> dict:
    try:
        if websocket is None:
            raise CaixaChromeError(_friendly_cdp_error(RuntimeError()))

        version = _get_json("/json/version")
        tabs = [
            tab
            for tab in _get_json("/json")
            if tab.get("type") == "page"
        ]
        abas_caixa = [
            {
                "title": tab.get("title", ""),
                "url": tab.get("url", ""),
            }
            for tab in tabs
            if "caixa" in (tab.get("url", "") + tab.get("title", "")).lower()
        ]

        return {
            "ok": True,
            "msg": (
                "Chrome controlavel conectado. "
                + (
                    "Aba da Caixa encontrada."
                    if abas_caixa
                    else "Abra ou acesse a Caixa neste Chrome antes de baixar."
                )
            ),
            "browser": version.get("Browser", ""),
            "tabs": len(tabs),
            "abas_caixa": abas_caixa,
        }
    except Exception as exc:
        return {
            "ok": False,
            "msg": _friendly_cdp_error(exc),
            "tabs": 0,
            "abas_caixa": [],
        }


class ChromeTab:
    def __init__(self, websocket_url: str):
        if websocket is None:
            raise CaixaChromeError(_friendly_cdp_error(RuntimeError()))

        self.ws = websocket.create_connection(websocket_url, timeout=8)
        self._next_id = 1

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

    def call(self, method: str, params: dict | None = None, timeout: float = 20.0):
        request_id = self._next_id
        self._next_id += 1
        self.ws.settimeout(timeout)
        self.ws.send(
            json.dumps(
                {
                    "id": request_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )

        while True:
            raw = self.ws.recv()
            payload = json.loads(raw)
            if payload.get("id") != request_id:
                continue

            if "error" in payload:
                message = payload["error"].get("message") or str(payload["error"])
                raise CaixaChromeError(f"{method}: {message}")

            return payload.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = False, timeout: float = 20.0):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
                "timeout": int(timeout * 1000),
            },
            timeout=timeout + 2,
        )

        if result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            text = details.get("text") or details.get("exception", {}).get("description")
            raise CaixaChromeError(text or "Erro ao executar comando no Chrome.")

        remote = result.get("result", {})
        if "value" in remote:
            return remote["value"]

        return remote.get("description")

    def set_download_path(self, download_path: Path):
        params = {
            "behavior": "allow",
            "downloadPath": str(download_path),
            "eventsEnabled": True,
        }

        try:
            self.call("Browser.setDownloadBehavior", params, timeout=5)
        except Exception:
            self.call("Page.setDownloadBehavior", params, timeout=5)


def _selecionar_aba_caixa() -> ChromeTab:
    tabs = [
        tab
        for tab in _get_json("/json")
        if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl")
    ]

    if not tabs:
        raise CaixaChromeError(
            "Nenhuma aba controlavel encontrada. Abra o Chrome pelo atalho do EMBASA."
        )

    tabs_ordenadas = sorted(
        tabs,
        key=lambda tab: (
            0 if "caixa" in (tab.get("url", "") + tab.get("title", "")).lower() else 1,
            tab.get("id", ""),
        ),
    )
    return ChromeTab(tabs_ordenadas[0]["webSocketDebuggerUrl"])


def _js_string(value: str) -> str:
    return json.dumps(str(value or ""), ensure_ascii=False)


def _sanitize_filename(nome: str) -> str:
    nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", str(nome or "")).strip()
    nome = re.sub(r"\s+", " ", nome)
    return nome or "extrato.pdf"


def _conta_curta(conta: str) -> str:
    texto = re.sub(r"\s+", "", str(conta or ""))
    match = re.search(r"(\d{4}-\d)$", texto)
    if match:
        return match.group(1)

    match = re.search(r"(\d{5}-\d)$", texto)
    if match:
        return match.group(1)

    return texto[-12:] or "CONTA"


def _nome_final(dados: dict, conta_site: str) -> str:
    nome = str(dados.get("nome_arquivo") or "").strip()
    conta_informada = str(dados.get("conta_arquivo") or "").strip()

    if nome and conta_informada and "CONTA_" not in nome:
        return _sanitize_filename(nome)

    mes = str(dados.get("mes") or "")
    sigla = str(dados.get("mes_sigla") or MESES_SIGLA.get(mes) or "MES")
    ano = str(dados.get("ano") or "")
    ano_curto = ano[-2:] if len(ano) >= 2 else "AA"
    return _sanitize_filename(f"CEF {_conta_curta(conta_site)}_{sigla}-{ano_curto}.pdf")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{stem} {timestamp}{suffix}")


def _snapshot_downloads(pasta: Path) -> set[str]:
    if not pasta.exists():
        return set()

    return {
        str(path.resolve()).lower()
        for path in pasta.glob("*")
        if path.is_file()
    }


def _aguardar_pdf(pasta: Path, antes: set[str], started_at: float, timeout: float = 180.0) -> Path:
    deadline = time.time() + timeout

    while time.time() < deadline:
        temporarios = list(pasta.glob("*.crdownload")) + list(pasta.glob("*.tmp"))
        pdfs = sorted(
            [
                path
                for path in pasta.glob("*.pdf")
                if path.is_file()
                and str(path.resolve()).lower() not in antes
                and path.stat().st_mtime >= started_at - 1
            ],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )

        if pdfs and not temporarios:
            return pdfs[0]

        time.sleep(1)

    raise CaixaChromeError(
        "O PDF nao apareceu na pasta destino. Confira se o Chrome abriu uma janela "
        "'Salvar como' ou se o download foi bloqueado."
    )


def _abrir_tela_extrato(tab: ChromeTab):
    script = f"""
(() => {{
  const path = {_js_string(CAIXA_EXTRATO_PATH)};
  const fallback = {_js_string(CAIXA_EXTRATO_URL)};
  const origem = location.origin && location.origin.startsWith('http')
    ? location.origin
    : '';
  const destino = origem ? `${{origem}}${{path}}` : fallback;
  if (!location.href.includes(path)) {{
    location.href = destino;
  }}
  return location.href;
}})()
"""
    tab.evaluate(script, timeout=10)

    wait_script = """
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const until = Date.now() + 60000;
  while (Date.now() < until) {
    if (document.querySelector('gcx-select[label="Selecione da lista"]')) {
      return true;
    }
    await sleep(500);
  }
  throw new Error("Tela Extrato individualizado nao carregou no Chrome.");
})()
"""
    tab.evaluate(wait_script, await_promise=True, timeout=65)


def _preparar_consulta(tab: ChromeTab, mes_label: str, ano: str) -> str:
    script = f"""
(async () => {{
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = (value) => String(value || '')
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .trim()
    .toLowerCase();

  const waitFor = async (fn, label, timeout = 20000) => {{
    const until = Date.now() + timeout;
    while (Date.now() < until) {{
      const value = fn();
      if (value) return value;
      await sleep(250);
    }}
    throw new Error(`${{label}} nao encontrado.`);
  }};

  const accountSelect = await waitFor(
    () => document.querySelector('gcx-select[label="Selecione da lista"]'),
    'Lista de contas'
  );

  const currentInput = accountSelect.querySelector('input[name="search-gcx-select"]');
  let contaSelecionada = currentInput && currentInput.value ? currentInput.value.trim() : '';

  if (!contaSelecionada) {{
    const opener = accountSelect.querySelector('.input-wrapper') || currentInput || accountSelect;
    opener.click();
    await sleep(700);
    const firstOption = await waitFor(
      () => [...document.querySelectorAll('button.dropdown-wrapper-item')]
        .find((button) => button.textContent.trim()),
      'Primeira conta da lista'
    );
    contaSelecionada = firstOption.textContent.trim();
    firstOption.click();
    await sleep(900);
  }}

  const selectDsc = async (label, optionText) => {{
    const component = await waitFor(
      () => [...document.querySelectorAll('dsc-select')]
        .find((item) => normalize(item.getAttribute('label')) === normalize(label)),
      `Campo ${{label}}`
    );
    const matSelect = component.querySelector('mat-select');
    if (!matSelect) throw new Error(`Combo ${{label}} nao possui mat-select.`);
    matSelect.click();
    await sleep(450);
    const option = await waitFor(
      () => [...document.querySelectorAll('mat-option')]
        .find((item) => normalize(item.textContent) === normalize(optionText)),
      `Opcao ${{optionText}}`
    );
    option.click();
    await sleep(650);
  }};

  await selectDsc('Mes', {_js_string(mes_label)});
  await selectDsc('Ano', {_js_string(ano)});

  const searchButton = await waitFor(
    () => document.querySelector('dsc-button[label="Pesquisar"] button'),
    'Botao Pesquisar'
  );

  if (searchButton.disabled) {{
    throw new Error('Botao Pesquisar ainda esta desabilitado apos selecionar mes e ano.');
  }}

  searchButton.click();
  await sleep(1000);

  await waitFor(
    () => document.querySelector('app-exportar-arquivo img[alt="icone-pdf"]')
      || document.body.textContent.includes('Nao foram encontrados')
      || document.body.textContent.includes('Não foram encontrados')
      || document.querySelector('component-listagem'),
    'Resultado da pesquisa',
    45000
  );

  return contaSelecionada;
}})()
"""
    return str(tab.evaluate(script, await_promise=True, timeout=75) or "").strip()


def _clicar_pdf(tab: ChromeTab):
    script = """
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const until = Date.now() + 30000;
  while (Date.now() < until) {
    const img = document.querySelector('app-exportar-arquivo img[alt="icone-pdf"]');
    const button = img && img.closest('button');
    if (button && !button.disabled) {
      button.click();
      return true;
    }
    await sleep(250);
  }
  throw new Error("Botao PDF nao encontrado ou desabilitado.");
})()
"""
    tab.evaluate(script, await_promise=True, timeout=35)


def executar_download_extrato_atual(
    dados: dict,
    log_callback=None,
    progress_callback=None,
    cancel_event=None,
) -> dict:
    def log(message: str, classe: str = ""):
        if callable(log_callback):
            log_callback(message, classe)

    def progress(message: str, percentual: int):
        if callable(progress_callback):
            progress_callback("BE", "processando", message, percentual)

    tab = None

    try:
        if cancel_event is not None and cancel_event.is_set():
            return {"ok": False, "cancelado": True, "msg": "Download cancelado."}

        mes = str(dados.get("mes") or "")
        ano = str(dados.get("ano") or "")
        mes_label = MESES_SITE.get(mes) or str(dados.get("mes_label") or "").strip()
        pasta_destino = Path(str(dados.get("pasta_destino") or "").strip())

        if not mes_label or not ano:
            raise CaixaChromeError("Informe mes e ano para baixar o extrato.")

        if not pasta_destino:
            raise CaixaChromeError("Pasta destino nao informada.")

        pasta_destino.mkdir(parents=True, exist_ok=True)

        progress("Conectando ao Chrome controlavel.", 10)
        log("Conectando ao Chrome controlavel na porta 9222.")
        tab = _selecionar_aba_caixa()
        tab.call("Page.enable", timeout=5)
        tab.call("Runtime.enable", timeout=5)
        tab.set_download_path(pasta_destino)

        progress("Abrindo Extrato individualizado da Caixa.", 25)
        _abrir_tela_extrato(tab)

        progress("Selecionando conta, mes e ano.", 45)
        conta_site = _preparar_consulta(tab, mes_label, ano)
        log(f"Conta preparada na Caixa: {conta_site or '--'}.")

        nome_final = _nome_final(dados, conta_site)
        destino_final = _unique_path(pasta_destino / nome_final)
        antes = _snapshot_downloads(pasta_destino)

        progress("Solicitando exportacao em PDF.", 70)
        inicio = time.time()
        _clicar_pdf(tab)

        progress("Aguardando download do PDF.", 85)
        arquivo_baixado = _aguardar_pdf(pasta_destino, antes, inicio)

        if arquivo_baixado.resolve() != destino_final.resolve():
            arquivo_baixado.rename(destino_final)

        progress("Extrato salvo com sucesso.", 100)
        log(f"Extrato Caixa salvo: {destino_final}.")

        return {
            "ok": True,
            "msg": "Extrato baixado com sucesso.",
            "conta": conta_site,
            "arquivo": str(destino_final),
            "pasta": str(pasta_destino),
        }
    except Exception as exc:
        mensagem = _friendly_cdp_error(exc)
        log(f"Falha ao baixar extrato Caixa: {mensagem}", "error")
        return {
            "ok": False,
            "msg": mensagem,
        }
    finally:
        if tab is not None:
            tab.close()
