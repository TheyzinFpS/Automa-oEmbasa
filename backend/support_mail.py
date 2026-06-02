from __future__ import annotations

import base64
import json
import mimetypes
import smtplib
import ssl
import tempfile
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from backend.settings import get_runtime_root, get_setting


MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024
SUPPORTED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_ATTACHMENT_MIME_TYPES = {"image/jpeg", "image/png"}


# Representa um anexo validado vindo da interface em base64.
@dataclass
class SupportAttachment:
    name: str
    size: int
    mime_type: str
    content_base64: str


# Converte valores de configuração textual para booleano.
def _setting_bool(value, default=False):
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    return str(value).strip().lower() in {"1", "true", "yes", "sim", "on"}


# Carrega apenas o bloco de configuração do Fale Conosco.
def _support_config() -> dict:
    return dict(get_setting("support", default={}) or {})


# Valida nome, tamanho, tipo e conteúdo base64 de cada anexo.
def _normalize_attachment(item: dict) -> SupportAttachment:
    if not isinstance(item, dict):
        raise ValueError("Formato inválido de anexo enviado pela interface.")

    name = Path(str(item.get("name") or "").strip()).name
    size_raw = item.get("size", 0)
    mime_type = str(item.get("type") or "").strip()
    content_base64 = str(item.get("content_base64") or "").strip()

    try:
        size = int(size_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Tamanho inválido para o anexo {name or 'sem nome'}.") from exc

    if not name:
        raise ValueError("Anexo sem nome identificado.")

    if size <= 0:
        raise ValueError(f"O anexo {name} está vazio.")

    if not content_base64:
        raise ValueError(f"O conteúdo do anexo {name} não foi recebido.")

    extension = Path(name).suffix.lower()
    guessed_type = mime_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
    normalized_type = guessed_type.lower()

    if extension not in SUPPORTED_ATTACHMENT_EXTENSIONS:
        raise ValueError(
            f"Tipo de arquivo não suportado: {name}. Use apenas JPG, JPEG ou PNG."
        )

    if normalized_type not in SUPPORTED_ATTACHMENT_MIME_TYPES:
        raise ValueError(
            f"Tipo de arquivo não suportado: {name}. Use apenas JPG, JPEG ou PNG."
        )

    return SupportAttachment(
        name=name,
        size=size,
        mime_type=normalized_type,
        content_base64=content_base64,
    )


# Normaliza todos os campos do pedido de atendimento.
def normalize_support_request(dados: dict) -> dict:
    matricula = str(dados.get("matricula", "")).strip()
    nome = str(dados.get("nome", "")).strip()
    lotacao = str(dados.get("lotacao", "")).strip()
    setor = str(dados.get("setor", "")).strip()
    descricao = str(dados.get("descricao", "")).strip()

    if not matricula:
        raise ValueError("Informe a matrícula.")

    if not nome:
        raise ValueError("Informe o nome.")

    if not lotacao:
        raise ValueError("Informe a lotação.")

    if not setor:
        raise ValueError("Informe o setor.")

    if not descricao:
        raise ValueError("Informe a descrição do atendimento.")

    if len(descricao) > 600:
        raise ValueError("A descrição deve ter no máximo 600 caracteres.")

    attachments = [
        _normalize_attachment(item)
        for item in (dados.get("imagens") or [])
    ]
    total_attachment_bytes = sum(item.size for item in attachments)

    if total_attachment_bytes > MAX_ATTACHMENT_BYTES:
        raise ValueError("Os anexos excedem o limite total de 15 MB.")

    return {
        "matricula": matricula,
        "nome": nome,
        "lotacao": lotacao,
        "setor": setor,
        "descricao": descricao,
        "attachments": attachments,
        "attachment_count": len(attachments),
        "attachment_total_bytes": total_attachment_bytes,
    }


# Monta o corpo do e-mail interno enviado para o atendimento.
def _build_support_body(payload: dict, protocolo: str) -> str:
    attachment_lines = [
        f"- {attachment.name} ({attachment.size} bytes)"
        for attachment in payload["attachments"]
    ]

    anexos = "\n".join(attachment_lines) if attachment_lines else "Nenhum anexo enviado."

    return (
        "Novo pedido de atendimento recebido pela API EMBASA.\n\n"
        f"Protocolo: {protocolo}\n"
        f"Matrícula: {payload['matricula']}\n"
        f"Nome: {payload['nome']}\n"
        f"Lotação: {payload['lotacao']}\n"
        f"Setor: {payload['setor']}\n"
        f"Quantidade de anexos: {payload['attachment_count']}\n\n"
        "Descrição:\n"
        f"{payload['descricao']}\n\n"
        "Anexos:\n"
        f"{anexos}\n"
    )


# Cria uma mensagem SMTP simples com assunto, remetente, destino e corpo.
def _build_email_message(
    subject: str,
    sender_name: str,
    sender_email: str,
    recipient_email: str,
    body: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((sender_name, sender_email))
    message["To"] = recipient_email
    message.set_content(body)
    return message


# Anexa os arquivos já validados na mensagem de suporte.
def _attach_files(message: EmailMessage, attachments: list[SupportAttachment]) -> None:
    for attachment in attachments:
        maintype, subtype = attachment.mime_type.split("/", 1) if "/" in attachment.mime_type else ("application", "octet-stream")
        message.add_attachment(
            _decode_attachment(attachment),
            maintype=maintype,
            subtype=subtype,
            filename=attachment.name,
        )


def _decode_attachment(attachment: SupportAttachment) -> bytes:
    try:
        content = base64.b64decode(attachment.content_base64, validate=True)
    except Exception as exc:
        raise ValueError(
            f"O conteúdo do anexo {attachment.name} está inválido."
        ) from exc

    if len(content) != attachment.size:
        raise ValueError(
            f"O tamanho recebido para o anexo {attachment.name} não confere."
        )

    return content


# Salva uma cópia local do atendimento para rastreio mesmo se o e-mail falhar.
def _save_support_snapshot(payload: dict, protocolo: str) -> str:
    snapshot_dir = get_runtime_root() / "atendimentos"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = snapshot_dir / f"{protocolo}.json"
    snapshot_payload = {
        "protocolo": protocolo,
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "matricula": payload["matricula"],
        "nome": payload["nome"],
        "lotacao": payload["lotacao"],
        "setor": payload["setor"],
        "descricao": payload["descricao"],
        "attachment_count": payload["attachment_count"],
        "attachment_total_bytes": payload["attachment_total_bytes"],
        "attachments": [
            {
                "name": attachment.name,
                "size": attachment.size,
                "mime_type": attachment.mime_type,
            }
            for attachment in payload["attachments"]
        ],
    }

    snapshot_path.write_text(
        json.dumps(snapshot_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(snapshot_path)


# Envia o atendimento usando um servidor SMTP configurado explicitamente.
def _send_support_email_smtp(payload: dict, protocolo: str, config: dict) -> dict:
    smtp_host = str(config.get("smtp_host") or "").strip()
    smtp_port = int(config.get("smtp_port") or 587)
    smtp_username = str(config.get("smtp_username") or "").strip()
    smtp_password = str(config.get("smtp_password") or "").strip()
    sender_email = str(config.get("smtp_from_email") or smtp_username).strip()
    sender_name = str(config.get("smtp_from_name") or "EMBASA API").strip()
    destination_email = str(config.get("destination_email") or "").strip()
    subject_prefix = str(config.get("subject_prefix") or "[EMBASA Atendimento]").strip()
    smtp_use_tls = _setting_bool(config.get("smtp_use_tls"), default=True)

    missing = [
        label
        for label, value in (
            ("smtp_host", smtp_host),
            ("smtp_port", smtp_port),
            ("smtp_from_email", sender_email),
            ("destination_email", destination_email),
        )
        if not value
    ]

    if missing:
        raise ValueError(
            "Configuração de e-mail incompleta. Ajuste: " + ", ".join(missing)
        )

    support_subject = f"{subject_prefix} {protocolo}"
    support_body = _build_support_body(payload, protocolo)
    support_message = _build_email_message(
        support_subject,
        sender_name,
        sender_email,
        destination_email,
        support_body,
    )
    _attach_files(support_message, payload["attachments"])

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.ehlo()

        if smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()

        if smtp_username:
            smtp.login(smtp_username, smtp_password)

        smtp.send_message(support_message)

    return {
        "destination_email": destination_email,
        "delivery_mode": "smtp",
    }


# Envia o atendimento pelo perfil já autenticado no Outlook clássico do Windows.
def _send_support_email_outlook(payload: dict, protocolo: str, config: dict) -> dict:
    destination_email = str(config.get("destination_email") or "").strip()
    subject_prefix = str(config.get("subject_prefix") or "[EMBASA Atendimento]").strip()

    if not destination_email:
        raise ValueError("Configuração de e-mail incompleta. Ajuste: destination_email")

    support_subject = f"{subject_prefix} {protocolo}"
    support_body = _build_support_body(payload, protocolo)
    pythoncom = None

    try:
        import pythoncom as pythoncom_module
        import win32com.client

        pythoncom_module.CoInitialize()
        pythoncom = pythoncom_module
        outlook = win32com.client.Dispatch("Outlook.Application")
        message = outlook.CreateItem(0)
        message.To = destination_email
        message.Subject = support_subject
        message.Body = support_body

        with tempfile.TemporaryDirectory(prefix="embasa_atendimento_") as temp_dir:
            for index, attachment in enumerate(payload["attachments"], start=1):
                attachment_path = Path(temp_dir) / f"{index:02d}_{attachment.name}"
                attachment_path.write_bytes(_decode_attachment(attachment))
                message.Attachments.Add(str(attachment_path))

            message.Send()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "Não foi possível enviar o atendimento pelo Outlook. "
            "Abra o Outlook corporativo, confirme que sua conta está conectada "
            "e tente novamente."
        ) from exc
    finally:
        if pythoncom is not None:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    return {
        "destination_email": destination_email,
        "delivery_mode": "outlook_desktop",
    }


# Envia o e-mail interno do pedido de atendimento.
def send_support_emails(payload: dict, protocolo: str) -> dict:
    config = _support_config()

    if not _setting_bool(config.get("notification_email_enabled"), default=False):
        raise ValueError("O envio por e-mail ainda não está configurado no sistema.")

    delivery_mode = str(config.get("delivery_mode") or "outlook_desktop").strip().lower()

    if delivery_mode == "outlook_desktop":
        return _send_support_email_outlook(payload, protocolo, config)

    if delivery_mode == "smtp":
        return _send_support_email_smtp(payload, protocolo, config)

    raise ValueError(
        "Modo de envio de atendimento inválido. Use outlook_desktop ou smtp."
    )


# Fluxo completo do Fale Conosco: validar, salvar protocolo e enviar e-mails.
def process_support_request(dados: dict) -> dict:
    payload = normalize_support_request(dados)
    protocolo = datetime.now().strftime("FAFTA-%Y%m%d-%H%M%S")
    snapshot_path = _save_support_snapshot(payload, protocolo)
    email_result = send_support_emails(payload, protocolo)

    return {
        "protocolo": protocolo,
        "snapshot_path": snapshot_path,
        **email_result,
    }
