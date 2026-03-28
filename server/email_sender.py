"""
Email sender — SMTP with optional file attachment.
Reads credentials from environment: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
"""

import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_path: str | None = None,
) -> dict:
    """
    Send an email via SMTP (Gmail or Outlook).
    Returns {"ok": True, "message": "..."} or raises on failure.
    """
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")

    if not user or not password:
        raise ValueError("SMTP_USER and SMTP_PASS must be set in server/.env")

    msg = MIMEMultipart()
    msg["From"]    = user
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach file if provided
    attached_name = None
    if attachment_path:
        file_path = Path(attachment_path).expanduser()
        if file_path.exists():
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=file_path.name)
            part["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
            msg.attach(part)
            attached_name = file_path.name
            logger.info("Attached file: %s", file_path.name)
        else:
            logger.error("Attachment file not found: %r (resolved: %r)", attachment_path, str(file_path))
            raise FileNotFoundError(f"Attachment not found: {file_path}")

    logger.info("Sending email to=%s subject=%r via %s:%d", to, subject, host, port)

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, to, msg.as_string())

    result = {"ok": True, "to": to, "subject": subject}
    if attached_name:
        result["attached"] = attached_name
    return result
