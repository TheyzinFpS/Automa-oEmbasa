from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import ctypes
from datetime import datetime


# Resolve arquivos tanto no codigo fonte quanto dentro do .exe do PyInstaller.
def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return str(base_path / relative_path)


# Define onde os erros de inicializacao ficam gravados no computador do usuario.
def startup_log_path() -> Path:
    log_dir = Path(tempfile.gettempdir()) / "EMBASA"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "startup.log"


# Grava diagnosticos simples antes da interface abrir.
def write_startup_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with startup_log_path().open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


# Exibe aviso nativo do Windows quando o app nao pode iniciar.
def show_startup_popup(message: str, title: str = "EMBASA") -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x30)
    except Exception:
        write_startup_log(f"Falha ao exibir popup: {message}")


# Identifica unidade de rede ou caminho UNC para evitar falha do .NET/pythonnet.
def is_network_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path

    text = str(resolved)

    if text.startswith("\\\\"):
        return True

    drive = resolved.drive

    if not drive:
        return False

    try:
        drive_root = f"{drive}\\"
        return ctypes.windll.kernel32.GetDriveTypeW(drive_root) == 4
    except Exception:
        return False


# Cria uma pasta local por build para executar o onedir fora da unidade de rede.
def local_runtime_dir(source_dir: Path) -> Path:
    exe_path = Path(sys.executable).resolve()

    try:
        stat = exe_path.stat()
        build_id = f"{int(stat.st_mtime)}_{stat.st_size}"
    except Exception:
        build_id = datetime.now().strftime("%Y%m%d%H%M%S")

    local_appdata = os.environ.get("LOCALAPPDATA")
    base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
    return base / "EMBASA" / "Runtime" / f"{source_dir.name}_{build_id}"


# Remove runtimes locais antigos sem afetar o build atual.
def cleanup_old_local_runtimes(current_dir: Path) -> None:
    runtime_root = current_dir.parent

    try:
        candidates = sorted(
            [
                item
                for item in runtime_root.iterdir()
                if item.is_dir() and item.name.startswith("EmbasaPedidosSAP")
            ],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return

    for old_dir in candidates[3:]:
        try:
            shutil.rmtree(old_dir, ignore_errors=True)
        except Exception:
            pass


# Mantem configuracoes editaveis da rede sincronizadas com a copia local.
def sync_runtime_config_files(source_dir: Path, target_dir: Path) -> None:
    for file_name in ("embasa_settings.json",):
        source_file = source_dir / file_name
        target_file = target_dir / file_name

        if not source_file.exists():
            continue

        try:
            shutil.copy2(source_file, target_file)
            write_startup_log(f"Configuracao sincronizada: {file_name}")
        except Exception:
            write_startup_log(f"Falha ao sincronizar configuracao: {file_name}")


# Se o exe estiver na rede, copia a pasta onedir para LOCALAPPDATA e relanca de la.
def relaunch_from_local_runtime_if_needed() -> bool:
    if not getattr(sys, "frozen", False):
        return False

    if os.environ.get("EMBASA_LOCAL_RUNTIME") == "1":
        return False

    source_dir = Path(sys.executable).resolve().parent

    if not is_network_path(source_dir):
        return False

    target_dir = local_runtime_dir(source_dir)
    target_exe = target_dir / Path(sys.executable).name

    try:
        write_startup_log(f"Executavel em rede detectado: {source_dir}")
        write_startup_log(f"Preparando runtime local: {target_dir}")

        if not target_exe.exists():
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)

            shutil.copytree(source_dir, target_dir)
            cleanup_old_local_runtimes(target_dir)

        sync_runtime_config_files(source_dir, target_dir)

        env = os.environ.copy()
        env["EMBASA_LOCAL_RUNTIME"] = "1"
        env["EMBASA_NETWORK_SOURCE"] = str(source_dir)

        subprocess.Popen(
            [str(target_exe), *sys.argv[1:]],
            cwd=str(target_dir),
            env=env,
            close_fds=True,
        )
        return True
    except Exception:
        write_startup_log("Falha ao preparar runtime local:")
        write_startup_log(traceback.format_exc())
        show_startup_popup(
            "Nao foi possivel preparar uma copia local do sistema.\n\n"
            "Feche o aplicativo e tente abrir novamente pela pasta da rede."
        )
        return True


# Permite ligar/desligar a obrigatoriedade de sessao SAP no arranque.
def require_sap_session_on_startup() -> bool:
    from backend.settings import get_setting

    raw_value = get_setting("startup", "require_sap_session", default=True)

    if isinstance(raw_value, bool):
        return raw_value

    normalized = str(raw_value or "").strip().lower()
    return normalized not in {"0", "false", "no", "nao", "off"}


class _WindowsRect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


# Calcula uma janela inicial que caiba na area util do monitor do usuario.
def calcular_tamanho_janela() -> tuple[int, int]:
    try:
        rect = _WindowsRect()
        workarea_ok = ctypes.windll.user32.SystemParametersInfoW(
            0x0030,
            0,
            ctypes.byref(rect),
            0,
        )

        if workarea_ok:
            screen_width = max(640, rect.right - rect.left)
            screen_height = max(520, rect.bottom - rect.top)
        else:
            screen_width = max(640, ctypes.windll.user32.GetSystemMetrics(0))
            screen_height = max(520, ctypes.windll.user32.GetSystemMetrics(1))
    except Exception:
        return 900, 800

    width = min(1180, max(820, int(screen_width * 0.9)))
    height = min(820, max(620, int(screen_height * 0.88)))

    width = min(width, max(640, screen_width - 32))
    height = min(height, max(520, screen_height - 48))

    return width, height


# Fluxo principal: valida SAP, cria a janela pywebview e conecta a API Python.
def main() -> None:
    write_startup_log(f"Iniciando app. frozen={getattr(sys, 'frozen', False)}")

    try:
        if relaunch_from_local_runtime_if_needed():
            return

        import webview

        from backend.sap_connection import diagnosticar_sap
        from interface import API

        interface_path = resource_path("interface/index.html")
        write_startup_log(f"Interface path: {interface_path}")

        if require_sap_session_on_startup():
            diagnostico_sap = diagnosticar_sap()

            if not diagnostico_sap["ok"]:
                write_startup_log(
                    "Inicializacao bloqueada: "
                    f"{diagnostico_sap.get('erro_tecnico') or 'sessao SAP indisponivel'}"
                )
                show_startup_popup(diagnostico_sap["mensagem"])
                return
        else:
            write_startup_log(
                "Verificacao inicial do SAP ignorada por configuracao local."
            )

        api = API()
        window_width, window_height = calcular_tamanho_janela()

        window = webview.create_window(
            "EMBASA",
            interface_path,
            js_api=api,
            width=window_width,
            height=window_height,
        )
        api.set_window(window)

        try:
            webview.start(gui="edgechromium")
        finally:
            api.stop()
    except Exception:
        write_startup_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
