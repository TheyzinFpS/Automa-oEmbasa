from pathlib import Path
import sys
import tempfile
import traceback
import ctypes
from datetime import datetime

import webview

from backend.sap_connection import diagnosticar_sap
from interface import API


def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return str(base_path / relative_path)


def startup_log_path() -> Path:
    log_dir = Path(tempfile.gettempdir()) / "EMBASA"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "startup.log"


def write_startup_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with startup_log_path().open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


def show_startup_popup(message: str, title: str = "EMBASA") -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x30)
    except Exception:
        write_startup_log(f"Falha ao exibir popup: {message}")


def main() -> None:
    interface_path = resource_path("interface/index.html")
    write_startup_log(f"Iniciando app. frozen={getattr(sys, 'frozen', False)}")
    write_startup_log(f"Interface path: {interface_path}")

    try:
        diagnostico_sap = diagnosticar_sap()

        if not diagnostico_sap["ok"]:
            write_startup_log(
                "Inicializacao bloqueada: "
                f"{diagnostico_sap.get('erro_tecnico') or 'sessao SAP indisponivel'}"
            )
            show_startup_popup(diagnostico_sap["mensagem"])
            return

        api = API()

        window = webview.create_window(
            "EMBASA",
            interface_path,
            js_api=api,
            width=900,
            height=800,
        )
        api.set_window(window)

        webview.start(gui="edgechromium")
    except Exception:
        write_startup_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
