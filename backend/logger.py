from datetime import datetime

from backend.security import mask_sensitive_text
from backend.settings import get_runtime_root, get_setting


# Logger central: separa logs técnicos de logs visíveis ao usuário final.
class Logger:
    def __init__(self):
        self.logs = []
        self.public_logs = []
        self.mask_documents_in_logs = bool(
            get_setting("security", "mask_documents_in_logs", default=True)
        )
        self.log_dir = get_runtime_root() / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file_path = self.log_dir / "processo_tecnico.log"

    # Persiste log tecnico em arquivo local para auditoria/debug.
    def _write_to_file(self, log):
        line = (
            f"[{log['timestamp']}] "
            f"[{log['nivel']}] "
            f"[ETAPA {log['etapa']}] "
            f"{log['msg']}\n"
        )

        try:
            with self.log_file_path.open("a", encoding="utf-8") as log_file:
                log_file.write(line)
        except OSError:
            return

    # Registra um evento e mascara documentos quando configurado.
    def add(self, etapa, msg, nivel="INFO", publico=False):
        safe_msg = str(msg or "")

        if self.mask_documents_in_logs:
            safe_msg = mask_sensitive_text(safe_msg)

        log = {
            "etapa": etapa,
            "msg": safe_msg,
            "nivel": nivel,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        self.logs.append(log)
        self._write_to_file(log)

        if publico:
            self.public_logs.append(log)

    def info(self, etapa, msg, publico=False):
        self.add(etapa, msg, "INFO", publico=publico)

    def erro(self, etapa, msg, publico=False):
        self.add(etapa, msg, "ERRO", publico=publico)

    def debug(self, etapa, msg, publico=False):
        self.add(etapa, msg, "DEBUG", publico=publico)

    # Retorna somente os logs publicos por padrao para nao poluir a interface.
    def get_logs(self, public_only=True):
        return self.public_logs if public_only else self.logs

    # Limpa a memoria de logs no inicio de um novo fluxo.
    def clear(self):
        self.logs.clear()
        self.public_logs.clear()
