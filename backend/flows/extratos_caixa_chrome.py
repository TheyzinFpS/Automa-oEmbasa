from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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

BROWSER_LABELS = {
    "opera": "Opera",
    "chrome": "Chrome",
    "edge": "Microsoft Edge",
}

BROWSER_PROCESS_NAMES = {
    "opera": "opera.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
}

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


def _normalizar_navegador(navegador: str | None) -> str:
    texto = str(navegador or "").strip().lower()
    if texto in {"opera", "chrome", "edge"}:
        return texto
    return "opera"


def _rotulo_navegador(navegador: str | None) -> str:
    return BROWSER_LABELS.get(_normalizar_navegador(navegador), "Opera")


def _candidatos_navegador(navegador: str | None) -> list[Path]:
    browser = _normalizar_navegador(navegador)
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("ProgramFiles", ""))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", ""))

    if browser == "opera":
        return [
            local / "Programs" / "Opera" / "opera.exe",
            local / "Programs" / "Opera" / "launcher.exe",
            local / "Programs" / "Opera GX" / "opera.exe",
            local / "Programs" / "Opera GX" / "launcher.exe",
            program_files / "Opera" / "opera.exe",
            program_files / "Opera" / "launcher.exe",
            program_files / "Opera GX" / "opera.exe",
            program_files / "Opera GX" / "launcher.exe",
            program_files_x86 / "Opera" / "opera.exe",
            program_files_x86 / "Opera" / "launcher.exe",
            program_files_x86 / "Opera GX" / "opera.exe",
            program_files_x86 / "Opera GX" / "launcher.exe",
        ]

    if browser == "edge":
        return [
            program_files_x86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            local / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]

    return [
        program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
        program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
        local / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]


def _encontrar_executavel_navegador(navegador: str | None) -> Path | None:
    for candidato in _candidatos_navegador(navegador):
        if candidato.exists():
            return candidato
    return None


def _get_json(path: str, timeout: float = 3.0):
    url = f"{CDP_BASE_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _is_remote_origin_error(exc: Exception) -> bool:
    texto = str(exc or "").lower()
    return (
        "403" in texto
        and (
            "remote-allow-origins" in texto
            or "rejected an incoming websocket connection" in texto
        )
    )


def _is_navigation_race_error(exc: Exception) -> bool:
    texto = str(exc or "").lower()
    return (
        "inspected target navigated or closed" in texto
        or "execution context was destroyed" in texto
        or "cannot find context with specified id" in texto
    )


def _friendly_cdp_error(exc: Exception, navegador: str | None = None) -> str:
    rotulo = _rotulo_navegador(navegador)

    if websocket is None:
        return (
            "Dependencia websocket-client ausente. Rode o rebuild para embutir "
            "a ponte de controle do navegador."
        )

    if _is_remote_origin_error(exc):
        return (
            f"{rotulo} esta aberto sem permissao de controle na porta 9222. "
            "Feche a janela do navegador controlavel, clique em Abrir navegador "
            "novamente e tente baixar os extratos."
        )

    if isinstance(exc, urllib.error.URLError):
        return (
            f"{rotulo} controlavel nao encontrado na porta 9222. "
            "Clique em Abrir navegador, faca login na Caixa e tente novamente."
        )

    return str(exc) or exc.__class__.__name__


def _gravar_json_seguro(path: Path, dados: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _carregar_json_seguro(path: Path) -> dict:
    try:
        if path.exists():
            dados = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(dados, dict):
                return dados
    except Exception:
        pass

    return {}


def _preparar_perfil_navegador(perfil: Path):
    preferences_path = perfil / "Default" / "Preferences"
    preferences = _carregar_json_seguro(preferences_path)
    profile = preferences.setdefault("profile", {})

    default_settings = profile.setdefault("default_content_setting_values", {})
    default_settings["geolocation"] = 2

    managed_settings = profile.setdefault("managed_default_content_settings", {})
    managed_settings["geolocation"] = 2

    content_settings = profile.setdefault("content_settings", {})
    exceptions = content_settings.setdefault("exceptions", {})
    geolocation = exceptions.setdefault("geolocation", {})
    geolocation["https://gerenciador.caixa.gov.br,*"] = {
        "last_modified": str(int(time.time() * 1000000)),
        "setting": 2,
    }

    _gravar_json_seguro(preferences_path, preferences)


def diagnosticar_chrome_caixa(navegador: str | None = None) -> dict:
    try:
        if websocket is None:
            raise CaixaChromeError(_friendly_cdp_error(RuntimeError(), navegador))

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

        teste_controle = _selecionar_aba_caixa()
        try:
            _bloquear_geolocalizacao_caixa(teste_controle)
        finally:
            teste_controle.close()

        return {
            "ok": True,
            "msg": (
                "Navegador controlavel conectado. "
                + (
                    "Aba da Caixa encontrada."
                    if abas_caixa
                    else "Abra ou acesse a Caixa neste navegador antes de baixar."
                )
            ),
            "browser": version.get("Browser", ""),
            "tabs": len(tabs),
            "abas_caixa": abas_caixa,
        }
    except Exception as exc:
        return {
            "ok": False,
            "msg": _friendly_cdp_error(exc, navegador),
            "tabs": 0,
            "abas_caixa": [],
        }


def abrir_navegador_caixa(navegador: str | None = None) -> dict:
    browser = _normalizar_navegador(navegador)
    rotulo = _rotulo_navegador(browser)

    diagnostico = diagnosticar_chrome_caixa(browser)
    if diagnostico.get("ok"):
        return {
            "ok": True,
            "msg": f"{rotulo} controlavel ja esta aberto.",
            "diagnostico": diagnostico,
        }

    if "sem permissao de controle" in str(diagnostico.get("msg") or ""):
        return {
            "ok": False,
            "msg": diagnostico.get("msg"),
            "diagnostico": diagnostico,
        }

    executavel = _encontrar_executavel_navegador(browser)
    if executavel is None:
        return {
            "ok": False,
            "msg": f"{rotulo} nao foi encontrado neste computador.",
        }

    perfil_base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EMBASA" / "BrowserCaixa"
    perfil = perfil_base / browser
    perfil.mkdir(parents=True, exist_ok=True)
    _preparar_perfil_navegador(perfil)

    args = [
        str(executavel),
        f"--remote-debugging-port={CDP_PORT}",
        f"--remote-allow-origins={CDP_BASE_URL}",
        f"--user-data-dir={perfil}",
        "--deny-permission-prompts",
        "--disable-geolocation",
        "--no-first-run",
        "--disable-features=Translate",
        CAIXA_EXTRATO_URL,
    ]

    try:
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception as exc:
        return {
            "ok": False,
            "msg": f"Falha ao abrir {rotulo}: {exc}",
        }

    deadline = time.time() + 12
    while time.time() < deadline:
        diagnostico = diagnosticar_chrome_caixa(browser)
        if diagnostico.get("ok"):
            return {
                "ok": True,
                "msg": f"{rotulo} controlavel aberto. Faca login na Caixa nesta janela.",
                "diagnostico": diagnostico,
            }
        time.sleep(0.6)

    return {
        "ok": False,
        "msg": (
            f"{rotulo} foi iniciado, mas a porta {CDP_PORT} ainda nao respondeu. "
            "Aguarde alguns segundos e tente baixar novamente."
        ),
    }


class ChromeTab:
    def __init__(self, websocket_url: str):
        if websocket is None:
            raise CaixaChromeError(_friendly_cdp_error(RuntimeError()))

        self.ws = websocket.create_connection(
            websocket_url,
            timeout=8,
            origin=CDP_BASE_URL,
        )
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


def _bloquear_geolocalizacao_caixa(tab: ChromeTab):
    payloads = [
        {"origin": "https://gerenciador.caixa.gov.br"},
        {"browserContextId": ""},
    ]

    for extra in payloads:
        params = {
            "permission": {"name": "geolocation"},
            "setting": "denied",
            **{key: value for key, value in extra.items() if value},
        }

        try:
            tab.call("Browser.setPermission", params, timeout=5)
        except Exception:
            continue


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


def _desktop_extratos_base() -> Path:
    candidatos = []

    for env_name in ("USERPROFILE", "OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        valor = os.environ.get(env_name)
        if valor:
            candidatos.append(Path(valor) / "Desktop")

    candidatos.append(Path.home() / "Desktop")

    for candidato in candidatos:
        if candidato.exists():
            return candidato / "EXTRATOS_CAIXA"

    return candidatos[0] / "EXTRATOS_CAIXA"


def _resolver_pasta_destino_extrato(dados: dict) -> Path:
    destino_informado = str(dados.get("pasta_destino") or "").strip()
    base_informada = str(dados.get("pasta_base") or "").strip()
    mes = str(dados.get("mes") or "")
    ano = str(dados.get("ano") or "")
    sigla = str(dados.get("mes_sigla") or MESES_SIGLA.get(mes) or "MES")

    if destino_informado:
        return Path(destino_informado)

    base = Path(base_informada) if base_informada else _desktop_extratos_base()

    if mes and ano:
        return base / ano / f"{mes}.{sigla}" / "CEF"

    return base


def _pastas_monitoradas_download(pasta_destino: Path) -> list[Path]:
    candidatos = [pasta_destino]

    for base in (
        os.environ.get("USERPROFILE"),
        os.environ.get("OneDriveCommercial"),
        os.environ.get("OneDriveConsumer"),
        os.environ.get("OneDrive"),
    ):
        if base:
            candidatos.append(Path(base) / "Downloads")

    candidatos.append(Path.home() / "Downloads")
    candidatos.append(Path.home() / "Desktop")

    vistos = set()
    pastas = []
    for pasta in candidatos:
        try:
            chave = str(pasta.resolve()).lower()
        except Exception:
            chave = str(pasta).lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        pastas.append(pasta)

    return pastas


def _normalizar_pastas(pastas: Path | list[Path] | tuple[Path, ...]) -> list[Path]:
    if isinstance(pastas, (list, tuple)):
        return [Path(pasta) for pasta in pastas]
    return [Path(pastas)]


def _snapshot_downloads(pastas: Path | list[Path] | tuple[Path, ...]) -> set[str]:
    arquivos = set()

    for pasta in _normalizar_pastas(pastas):
        if not pasta.exists():
            continue

        arquivos.update(
            str(path.resolve()).lower()
            for path in pasta.glob("*")
            if path.is_file()
        )

    return arquivos


def _aguardar_pdf(
    pastas: Path | list[Path] | tuple[Path, ...],
    antes: set[str],
    started_at: float,
    timeout: float = 180.0,
) -> Path:
    deadline = time.time() + timeout
    pastas_monitoradas = _normalizar_pastas(pastas)

    while time.time() < deadline:
        temporarios = []
        pdfs = []

        for pasta in pastas_monitoradas:
            if not pasta.exists():
                continue

            temporarios.extend(list(pasta.glob("*.crdownload")) + list(pasta.glob("*.tmp")))
            pdfs.extend(
                [
                    path
                    for path in pasta.glob("*.pdf")
                    if path.is_file()
                    and str(path.resolve()).lower() not in antes
                    and path.stat().st_mtime >= started_at - 1
                ]
            )

        pdfs = sorted(
            pdfs,
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


def _mover_pdf_para_destino(origem: Path, destino: Path, timeout: float = 35.0) -> Path:
    origem = Path(origem)
    destino = Path(destino)

    if origem.resolve() == destino.resolve():
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    ultimo_erro = None

    while time.time() < deadline:
        try:
            if destino.exists():
                destino = _unique_path(destino)
            shutil.move(str(origem), str(destino))
            return destino
        except OSError as exc:
            ultimo_erro = exc
            time.sleep(0.5)

    raise CaixaChromeError(
        "O PDF foi baixado, mas nao consegui aplicar o nome padrao. "
        f"Origem: {origem}. Destino: {destino}. Erro: {ultimo_erro}"
    )


def _aguardar_tela_extrato(tab: ChromeTab, timeout_seconds: int = 45) -> bool:
    wait_script = f"""
(async () => {{
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const until = Date.now() + {int(timeout_seconds * 1000)};
  while (Date.now() < until) {{
    if (document.querySelector('gcx-select[label="Selecione da lista"]')) {{
      return true;
    }}
    await sleep(500);
  }}
  throw new Error("Tela Extrato individualizado nao carregou no Chrome.");
}})()
"""
    ultimo_erro = None
    for _ in range(4):
        try:
            tab.evaluate(wait_script, await_promise=True, timeout=timeout_seconds + 5)
            return True
        except Exception as exc:
            ultimo_erro = exc
            if _is_navigation_race_error(exc):
                time.sleep(1.2)
                continue

            if "Tela Extrato individualizado nao carregou" in str(exc):
                return False

            raise

    if ultimo_erro and not _is_navigation_race_error(ultimo_erro):
        raise ultimo_erro

    return False


def _clicar_menu_extrato(tab: ChromeTab) -> str:
    script = """
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = (value) => String(value || '')
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .replace(/\\s+/g, ' ')
    .trim()
    .toLowerCase();

  const clickElement = (element) => {
    element.scrollIntoView({ block: 'center', inline: 'center' });
    element.focus();
    element.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    element.click();
  };

  if (document.querySelector('gcx-select[label="Selecione da lista"]')) {
    return 'extrato-ja-aberto';
  }

  const saldoButton = [...document.querySelectorAll('button')]
    .find((button) => normalize(button.textContent).includes('saldo e extratos'));

  if (saldoButton) {
    clickElement(saldoButton);
    await sleep(900);
  }

  const until = Date.now() + 10000;
  while (Date.now() < until) {
    const links = [...document.querySelectorAll('a[href]')];
    const target = links
      .find((element) => (element.getAttribute('href') || '').includes('/empresa/dashboard/govconta/selecao-govconta/extrato-individualizado'))
      || links
      .find((element) => {
        const text = normalize(element.textContent);
        const href = normalize(element.getAttribute('href') || '');
        return text.includes('extrato individualizado de contas')
          || href.includes('extrato-individualizado');
      });

    if (target) {
      const href = target.getAttribute('href') || '';
      clickElement(target);
      await sleep(1200);

      if (document.querySelector('gcx-select[label="Selecione da lista"]')
        || location.href.includes('extrato-individualizado')) {
        return 'menu-extrato-clicado';
      }

      if (href) {
        const url = href.startsWith('http')
          ? href
          : `${location.origin}${href.startsWith('/') ? '' : '/'}${href}`;
        location.href = url;
        return 'menu-extrato-href-aplicado';
      }

      return 'menu-extrato-clicado-sem-href';
    }

    await sleep(250);
  }

  return 'menu-extrato-nao-encontrado';
})()
"""
    return str(tab.evaluate(script, await_promise=True, timeout=15) or "")


def _abrir_tela_extrato(tab: ChromeTab):
    if _aguardar_tela_extrato(tab, timeout_seconds=2):
        return

    try:
        resultado_menu = _clicar_menu_extrato(tab)
    except Exception as exc:
        if not _is_navigation_race_error(exc):
            raise
        resultado_menu = "navegacao-em-andamento"

    if resultado_menu != "menu-extrato-nao-encontrado":
        if _aguardar_tela_extrato(tab, timeout_seconds=45):
            return

    try:
        tab.call("Page.navigate", {"url": CAIXA_EXTRATO_URL}, timeout=10)
    except Exception as exc:
        if not _is_navigation_race_error(exc):
            raise

    time.sleep(1.2)

    if _aguardar_tela_extrato(tab, timeout_seconds=45):
        return

    raise CaixaChromeError(
        "Nao consegui abrir a tela Extrato Individualizado. "
        "Confirme se o menu Saldo e Extratos aparece no Gerenciador Caixa "
        "e tente novamente."
    )


def _listar_contas(tab: ChromeTab) -> list[str]:
    script = """
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const waitFor = async (fn, label, timeout = 20000) => {
    const until = Date.now() + timeout;
    while (Date.now() < until) {
      const value = fn();
      if (value) return value;
      await sleep(250);
    }
    throw new Error(`${label} nao encontrado.`);
  };

  const accountSelect = await waitFor(
    () => document.querySelector('gcx-select[label="Selecione da lista"]'),
    'Lista de contas'
  );
  const opener = accountSelect.querySelector('.input-wrapper')
    || accountSelect.querySelector('input[name="search-gcx-select"]')
    || accountSelect;
  opener.click();
  await sleep(700);

  const contas = new Set();
  const coletarVisiveis = () => {
    [...document.querySelectorAll('button.dropdown-wrapper-item')]
      .map((button) => button.textContent.trim())
      .filter(Boolean)
      .forEach((texto) => contas.add(texto));
  };

  const viewport = document.querySelector('.cdk-virtual-scroll-viewport.dropdown-wrapper')
    || document.querySelector('.cdk-virtual-scroll-viewport');

  coletarVisiveis();

  if (viewport) {
    viewport.scrollTop = 0;
    viewport.dispatchEvent(new Event('scroll', { bubbles: true }));
    await sleep(250);
    coletarVisiveis();

    for (let index = 0; index < 120; index += 1) {
      const limite = Math.max(0, viewport.scrollHeight - viewport.clientHeight);
      if (viewport.scrollTop >= limite - 4) break;
      viewport.scrollTop = Math.min(
        limite,
        viewport.scrollTop + Math.max(120, viewport.clientHeight - 20)
      );
      viewport.dispatchEvent(new Event('scroll', { bubbles: true }));
      await sleep(220);
      coletarVisiveis();
    }
  }

  const input = accountSelect.querySelector('input[name="search-gcx-select"]');
  if (input && input.value.trim()) {
    contas.add(input.value.trim());
  }

  document.dispatchEvent(new KeyboardEvent('keydown', {
    key: 'Escape',
    code: 'Escape',
    bubbles: true
  }));

  return [...contas];
})()
"""
    contas = tab.evaluate(script, await_promise=True, timeout=55) or []

    if not isinstance(contas, list):
        return []

    normalizadas = []
    vistos = set()
    for conta in contas:
        texto = str(conta or "").strip()
        chave = re.sub(r"\D+", "", texto)
        if not texto or not chave or chave in vistos:
            continue
        vistos.add(chave)
        normalizadas.append(texto)

    return normalizadas


def _preparar_consulta(tab: ChromeTab, mes_label: str, ano: str, conta_alvo: str | None = None) -> str:
    script = f"""
(async () => {{
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const contaAlvo = {_js_string(conta_alvo or '')};
  const normalize = (value) => String(value || '')
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .trim()
    .toLowerCase();
  const onlyDigits = (value) => String(value || '').replace(/\\D/g, '');
  const sameAccount = (left, right) => {{
    const leftDigits = onlyDigits(left);
    const rightDigits = onlyDigits(right);
    return normalize(left) === normalize(right)
      || (leftDigits && rightDigits && leftDigits === rightDigits);
  }};

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

  const campoDsc = (label) => [...document.querySelectorAll('dsc-select')]
    .find((item) => normalize(item.getAttribute('label')) === normalize(label));

  const textoDetalheConta = () => [
    ...document.querySelectorAll('.detalhes-consulta, .resumo-wrapper, .resumo, .conta-nome')
  ].map((item) => item.textContent || '').join(' ');

  const valorContaSelecionada = () => {{
    const searchValue = currentInput && currentInput.value ? currentInput.value.trim() : '';
    if (searchValue) return searchValue;

    const hiddenValue = accountSelect.querySelector('input[type="hidden"]')?.value?.trim() || '';
    if (hiddenValue) return hiddenValue;

    return (accountSelect.querySelector('.input-wrapper')?.textContent || accountSelect.textContent || '').trim();
  }};

  const camposPeriodoDisponiveis = () => Boolean(campoDsc('Mes') && campoDsc('Ano'));
  const contaSelecionadaNoCampo = (contaEsperada = '') => {{
    const alvoDigits = onlyDigits(contaEsperada);
    if (!alvoDigits) return true;
    return sameAccount(valorContaSelecionada(), contaEsperada);
  }};

  const contaReferenciaAtualizada = (contaEsperada = '') => {{
    const alvoDigits = onlyDigits(contaEsperada);
    if (!alvoDigits) return true;
    return onlyDigits(textoDetalheConta()).includes(alvoDigits);
  }};

  const camposPeriodoProntos = (contaEsperada = '') => (
    camposPeriodoDisponiveis() && contaSelecionadaNoCampo(contaEsperada)
  );

  const isVisible = (element) => {{
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0
      && rect.height > 0
      && style.display !== 'none'
      && style.visibility !== 'hidden';
  }};

  const accountButtons = () => [...document.querySelectorAll('button.dropdown-wrapper-item')]
    .filter((button) => isVisible(button) && button.textContent.trim());

  const findAccountButton = (conta) => accountButtons()
    .find((button) => sameAccount(button.textContent, conta))
    || accountButtons()
      .find((button) => normalize(button.textContent).includes(normalize(conta)));

  const forceClick = async (element) => {{
    element.scrollIntoView({{ block: 'center', inline: 'nearest' }});
    await sleep(120);
    const rect = element.getBoundingClientRect();
    const clientX = rect.left + Math.min(Math.max(rect.width / 2, 8), Math.max(rect.width - 8, 8));
    const clientY = rect.top + Math.min(Math.max(rect.height / 2, 8), Math.max(rect.height - 8, 8));
    const eventBase = {{
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0,
      buttons: 1,
      clientX,
      clientY,
    }};
    const pointerBase = {{
      ...eventBase,
      pointerId: 1,
      pointerType: 'mouse',
      isPrimary: true,
    }};

    const PointerCtor = window.PointerEvent || window.MouseEvent;
    element.dispatchEvent(new PointerCtor('pointerover', pointerBase));
    element.dispatchEvent(new MouseEvent('mouseover', eventBase));
    element.dispatchEvent(new PointerCtor('pointermove', pointerBase));
    element.dispatchEvent(new MouseEvent('mousemove', eventBase));
    element.dispatchEvent(new PointerCtor('pointerdown', pointerBase));
    element.dispatchEvent(new MouseEvent('mousedown', eventBase));
    if (typeof element.focus === 'function') {{
      element.focus({{ preventScroll: true }});
    }}
    element.dispatchEvent(new PointerCtor('pointerup', {{ ...pointerBase, buttons: 0 }}));
    element.dispatchEvent(new MouseEvent('mouseup', {{ ...eventBase, buttons: 0 }}));
    element.dispatchEvent(new MouseEvent('click', {{ ...eventBase, buttons: 0 }}));
  }};

  const abrirListaContas = async () => {{
    const opener = accountSelect.querySelector('.input-wrapper') || currentInput || accountSelect;
    if (!accountButtons().length) {{
      await forceClick(opener);
      await sleep(500);
    }}

    const viewport = document.querySelector('.cdk-virtual-scroll-viewport.dropdown-wrapper')
      || document.querySelector('.cdk-virtual-scroll-viewport');
    if (viewport) {{
      viewport.scrollTop = 0;
      viewport.dispatchEvent(new Event('scroll', {{ bubbles: true }}));
      await sleep(180);
    }}
  }};

  const filtrarConta = async (conta) => {{
    if (!currentInput) return;
    currentInput.focus();
    currentInput.value = '';
    currentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    currentInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
    await sleep(160);
    currentInput.value = conta;
    currentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    currentInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
    await sleep(650);
  }};

  const confirmarCamposPeriodo = async (conta, timeout = 9000) => {{
    try {{
      await waitFor(
        () => camposPeriodoProntos(conta),
        `Campos de mes e ano para a conta ${{conta}}`,
        timeout
      );
      return true;
    }} catch (error) {{
      return false;
    }}
  }};

  const selecionarOpcaoConta = async (conta) => {{
    await abrirListaContas();

    let option = findAccountButton(conta);
    if (!option) {{
      await filtrarConta(conta);
      option = await waitFor(
        () => findAccountButton(conta),
        `Conta ${{conta}}`
      );
    }}

    const textoSelecionado = option.textContent.trim();
    await forceClick(option);
    await sleep(850);

    if (await confirmarCamposPeriodo(conta, 4500)) {{
      return textoSelecionado;
    }}

    await abrirListaContas();
    option = findAccountButton(conta);
    if (!option) {{
      await filtrarConta(conta);
      option = await waitFor(
        () => findAccountButton(conta),
        `Conta ${{conta}} apos nova tentativa`
      );
    }}

    option.focus();
    option.dispatchEvent(new KeyboardEvent('keydown', {{
      key: 'Enter',
      code: 'Enter',
      bubbles: true,
      cancelable: true,
    }}));
    option.dispatchEvent(new KeyboardEvent('keyup', {{
      key: 'Enter',
      code: 'Enter',
      bubbles: true,
      cancelable: true,
    }}));
    await sleep(500);

    if (!(await confirmarCamposPeriodo(conta, 4500))) {{
      await forceClick(option);
      await sleep(850);
    }}

    if (!(await confirmarCamposPeriodo(conta, 6500))) {{
      throw new Error(
        `A conta ${{conta}} apareceu na lista, mas o site nao abriu os campos Mes/Ano apos o clique.`
      );
    }}

    return textoSelecionado;
  }};

  const selecionarConta = async (conta) => {{
    if (contaSelecionada && sameAccount(contaSelecionada, conta) && camposPeriodoProntos(conta)) {{
      return contaSelecionada;
    }}

    contaSelecionada = await selecionarOpcaoConta(conta);
    return contaSelecionada;
  }};

  if (contaAlvo) {{
    contaSelecionada = await selecionarConta(contaAlvo);
  }} else if (!contaSelecionada) {{
    await abrirListaContas();
    const firstOption = await waitFor(
      () => accountButtons().find((button) => button.textContent.trim()),
      'Primeira conta da lista'
    );
    contaSelecionada = firstOption.textContent.trim();
    await forceClick(firstOption);
    await sleep(900);
    await waitFor(
      () => camposPeriodoProntos(contaSelecionada),
      `Campos de mes e ano para a conta ${{contaSelecionada}}`
    );
  }}

  const selectDsc = async (label, optionText) => {{
    const component = await waitFor(
      () => campoDsc(label),
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

  const textoResultadoAntes = (document.querySelector('component-listagem')?.innerText || '').trim();
  const linhasAntes = document.querySelectorAll(
    'component-listagem tr, component-listagem [role="row"]'
  ).length;
  const inicioPesquisa = Date.now();
  const contaPesquisa = contaSelecionada || contaAlvo || '';

  await forceClick(searchButton);
  await sleep(900);

  await waitFor(
    () => document.querySelector('app-exportar-arquivo img[alt="icone-pdf"]')
      || document.body.textContent.includes('Nao foram encontrados')
      || document.body.textContent.includes('Não foram encontrados')
      || document.querySelector('component-listagem'),
    'Resultado da pesquisa',
    45000
  );

  await waitFor(
    () => {{
      const tempoDecorrido = Date.now() - inicioPesquisa;
      if (tempoDecorrido < 2600) return false;
      if (!contaReferenciaAtualizada(contaPesquisa)) return false;

      const textoPagina = document.body.textContent || '';
      if (
        textoPagina.includes('Nao foram encontrados')
        || textoPagina.includes('NÃ£o foram encontrados')
      ) {{
        return 'sem-registros';
      }}

      const listagem = document.querySelector('component-listagem');
      const textoResultadoAtual = (listagem?.innerText || '').trim();
      const linhasAtual = document.querySelectorAll(
        'component-listagem tr, component-listagem [role="row"]'
      ).length;
      const pdfButton = document.querySelector('app-exportar-arquivo img[alt="icone-pdf"]')
        ?.closest('button');
      if (pdfButton && !pdfButton.disabled && tempoDecorrido > 3600) {{
        return 'pdf-disponivel-apos-pesquisa';
      }}

      const resultadoMudou = textoResultadoAtual
        && (
          textoResultadoAtual !== textoResultadoAntes
          || linhasAtual !== linhasAntes
          || tempoDecorrido > 5200
        );

      if (listagem && resultadoMudou && pdfButton && !pdfButton.disabled) {{
        return 'resultado-atualizado';
      }}

      return false;
    }},
    `Resultado da pesquisa da conta ${{contaPesquisa}}`,
    45000
  );

  await sleep(600);
  return contaSelecionada;
}})()
"""
    return str(tab.evaluate(script, await_promise=True, timeout=75) or "").strip()


def _clicar_pdf(tab: ChromeTab):
    script = """
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const isVisible = (element) => {
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0
      && rect.height > 0
      && style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.opacity !== '0'
      && !element.closest('[hidden], .hidden');
  };

  const findPdfButton = () => {
    const images = [
      ...document.querySelectorAll(
        'app-exportar-arquivo img[alt="icone-pdf"], app-exportar-arquivo img[src*="pdf"]'
      )
    ];

    const buttons = images
      .map((img) => img.closest('button'))
      .filter(Boolean)
      .filter((button) => (
        isVisible(button)
        && !button.disabled
        && button.getAttribute('aria-disabled') !== 'true'
      ));

    return buttons[buttons.length - 1] || null;
  };

  const forceClick = async (element) => {
    element.scrollIntoView({ block: 'center', inline: 'nearest' });
    await sleep(120);
    const rect = element.getBoundingClientRect();
    const clientX = rect.left + Math.min(Math.max(rect.width / 2, 8), Math.max(rect.width - 8, 8));
    const clientY = rect.top + Math.min(Math.max(rect.height / 2, 8), Math.max(rect.height - 8, 8));
    const eventBase = {
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0,
      buttons: 1,
      clientX,
      clientY,
    };
    const pointerBase = {
      ...eventBase,
      pointerId: 1,
      pointerType: 'mouse',
      isPrimary: true,
    };
    const PointerCtor = window.PointerEvent || window.MouseEvent;
    element.dispatchEvent(new PointerCtor('pointerover', pointerBase));
    element.dispatchEvent(new MouseEvent('mouseover', eventBase));
    element.dispatchEvent(new PointerCtor('pointerdown', pointerBase));
    element.dispatchEvent(new MouseEvent('mousedown', eventBase));
    if (typeof element.focus === 'function') {
      element.focus({ preventScroll: true });
    }
    element.dispatchEvent(new PointerCtor('pointerup', { ...pointerBase, buttons: 0 }));
    element.dispatchEvent(new MouseEvent('mouseup', { ...eventBase, buttons: 0 }));
    element.dispatchEvent(new MouseEvent('click', { ...eventBase, buttons: 0 }));
    if (typeof element.click === 'function') {
      element.click();
    }
  };

  const until = Date.now() + 30000;
  while (Date.now() < until) {
    const texto = document.body.textContent || '';
    if (texto.includes('Nao foram encontrados') || texto.includes('Não foram encontrados')) {
      throw new Error('Nenhum lancamento encontrado para esta conta no periodo.');
    }

    const button = findPdfButton();
    if (button) {
      await forceClick(button);
      await sleep(350);
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

    def progress_resultado(item: dict):
        if callable(progress_callback):
            progress_callback(
                "BE",
                "processando",
                "EXTRATO_RESULT::" + json.dumps(item, ensure_ascii=False),
                None,
            )

    tab = None

    try:
        if cancel_event is not None and cancel_event.is_set():
            return {"ok": False, "cancelado": True, "msg": "Download cancelado."}

        mes = str(dados.get("mes") or "")
        ano = str(dados.get("ano") or "")
        navegador = _normalizar_navegador(dados.get("navegador"))
        rotulo_navegador = _rotulo_navegador(navegador)
        mes_label = MESES_SITE.get(mes) or str(dados.get("mes_label") or "").strip()
        pasta_destino = _resolver_pasta_destino_extrato(dados)

        if not mes_label or not ano:
            raise CaixaChromeError("Informe mes e ano para baixar o extrato.")

        if not pasta_destino:
            raise CaixaChromeError("Pasta destino nao informada.")

        pasta_destino.mkdir(parents=True, exist_ok=True)
        pastas_monitoradas = _pastas_monitoradas_download(pasta_destino)

        progress(f"Conectando ao {rotulo_navegador} controlavel.", 10)
        log(f"Conectando ao {rotulo_navegador} controlavel na porta 9222.")
        tab = _selecionar_aba_caixa()
        tab.call("Page.enable", timeout=5)
        tab.call("Runtime.enable", timeout=5)
        _bloquear_geolocalizacao_caixa(tab)
        tab.set_download_path(pasta_destino)

        progress("Abrindo Extrato individualizado da Caixa.", 25)
        _abrir_tela_extrato(tab)

        progress("Mapeando contas disponiveis.", 30)
        contas = _listar_contas(tab)
        if not contas:
            raise CaixaChromeError("Nenhuma conta foi encontrada na lista do GovConta.")

        log(f"Contas Caixa encontradas para baixa: {len(contas)}.")

        resultados = []
        total = max(1, len(contas))

        for indice, conta_alvo in enumerate(contas, start=1):
            if cancel_event is not None and cancel_event.is_set():
                return {
                    "ok": False,
                    "cancelado": True,
                    "msg": "Download cancelado.",
                    "itens": resultados,
                }

            percentual_base = 30 + int(((indice - 1) / total) * 65)

            try:
                progress(f"Conta {indice}/{total}: selecionando dados.", percentual_base)
                conta_site = _preparar_consulta(tab, mes_label, ano, conta_alvo)
                log(f"Conta preparada na Caixa ({indice}/{total}): {conta_site or conta_alvo}.")

                nome_final = _nome_final(dados, conta_site or conta_alvo)
                destino_final = _unique_path(pasta_destino / nome_final)
                antes = _snapshot_downloads(pastas_monitoradas)

                progress(f"Conta {indice}/{total}: exportando PDF.", min(95, percentual_base + 8))
                arquivo_baixado = None
                ultimo_erro_download = None

                for tentativa_pdf, timeout_pdf in enumerate((25, 35, 120), start=1):
                    inicio = time.time()
                    _clicar_pdf(tab)

                    progress(
                        f"Conta {indice}/{total}: aguardando download.",
                        min(98, percentual_base + 14),
                    )
                    try:
                        arquivo_baixado = _aguardar_pdf(
                            pastas_monitoradas,
                            antes,
                            inicio,
                            timeout=timeout_pdf,
                        )
                        break
                    except Exception as download_exc:
                        ultimo_erro_download = download_exc
                        if tentativa_pdf >= 3:
                            break

                        log(
                            "PDF da conta "
                            f"{conta_site or conta_alvo} nao apareceu apos o clique "
                            f"(tentativa {tentativa_pdf}/3). Repetindo clique no PDF.",
                            "warning",
                        )
                        time.sleep(1.2)

                if arquivo_baixado is None:
                    raise ultimo_erro_download or CaixaChromeError(
                        "O PDF nao foi baixado apos repetir o clique no botao PDF."
                    )

                arquivo_final = _mover_pdf_para_destino(arquivo_baixado, destino_final)

                item_resultado = {
                    "status": "ok",
                    "conta": conta_site or conta_alvo,
                    "arquivo": str(arquivo_final),
                }
                resultados.append(item_resultado)
                progress_resultado(item_resultado)
                log(f"Extrato Caixa salvo ({indice}/{total}): {arquivo_final}.")
            except Exception as item_exc:
                mensagem_item = _friendly_cdp_error(item_exc, navegador)
                item_resultado = {
                    "status": "erro",
                    "conta": conta_alvo or "--",
                    "erro": mensagem_item,
                }
                resultados.append(item_resultado)
                progress_resultado(item_resultado)
                log(f"Falha na conta Caixa {conta_alvo or '--'}: {mensagem_item}", "error")

                try:
                    _abrir_tela_extrato(tab)
                except Exception:
                    pass

        baixados = [item for item in resultados if item.get("status") == "ok"]
        erros = len(resultados) - len(baixados)

        if not baixados:
            progress("Nenhum extrato foi baixado.", 100)
            return {
                "ok": False,
                "msg": "Nenhum extrato Caixa foi baixado.",
                "pasta": str(pasta_destino),
                "itens": resultados,
            }

        progress("Baixa de extratos finalizada.", 100)
        log(f"Baixa Caixa finalizada. Baixados: {len(baixados)}. Erros: {erros}.")
        primeiro = baixados[0]

        return {
            "ok": True,
            "msg": (
                "Extratos baixados com sucesso."
                if not erros
                else "Extratos baixados com alertas."
            ),
            "conta": primeiro.get("conta", ""),
            "arquivo": primeiro.get("arquivo", ""),
            "pasta": str(pasta_destino),
            "itens": resultados,
        }
    except Exception as exc:
        mensagem = _friendly_cdp_error(exc, dados.get("navegador") if isinstance(dados, dict) else None)
        log(f"Falha ao baixar extrato Caixa: {mensagem}", "error")
        return {
            "ok": False,
            "msg": mensagem,
            "itens": [
                {
                    "status": "erro",
                    "conta": str(dados.get("conta") or dados.get("conta_arquivo") or "--") if isinstance(dados, dict) else "--",
                    "erro": mensagem,
                }
            ],
        }
    finally:
        if tab is not None:
            tab.close()
