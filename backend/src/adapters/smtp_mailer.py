"""Mailers: real SMTP for preview/prod, a logging stand-in for dev and tests."""

import logging
import smtplib
from email.message import EmailMessage

from src.core.exceptions import MailerError
from src.core.interfaces.mailer import Attachment, Mailer

logger = logging.getLogger(__name__)


class LoggingMailer(Mailer):
    """Logs instead of sending and keeps every message for tests to inspect."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, to: str, subject: str, text: str, attachments: list[Attachment]) -> None:
        self.sent.append({"to": to, "subject": subject, "text": text, "attachments": attachments})
        logger.info(
            "mail (not sent): to=%s subject=%r attachments=%s",
            to,
            subject,
            [a.filename for a in attachments],
        )


class SmtpMailer(Mailer):
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        user: str | None = None,
        password: str | None = None,
        starttls: bool = True,
        timeout: float = 15.0,
    ) -> None:
        self._host, self._port, self._sender = host, port, sender
        self._user, self._password = user, password
        self._starttls, self._timeout = starttls, timeout

    def send(self, to: str, subject: str, text: str, attachments: list[Attachment]) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)
        for attachment in attachments:
            maintype, _, subtype = attachment.media_type.partition("/")
            message.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype or "octet-stream",
                filename=attachment.filename,
            )
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                if self._starttls:
                    smtp.starttls()
                if self._user:
                    smtp.login(self._user, self._password or "")
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailerError(f"could not send mail: {exc}") from exc
