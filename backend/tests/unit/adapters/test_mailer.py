from email import message_from_bytes

import pytest

from src.adapters.smtp_mailer import LoggingMailer, SmtpMailer
from src.core.exceptions import MailerError
from src.core.interfaces.mailer import Attachment


def test_logging_mailer_records_messages() -> None:
    mailer = LoggingMailer()
    mailer.send("to@example.com", "Hi", "body", [Attachment("a.txt", b"x", "text/plain")])
    assert mailer.sent[0]["to"] == "to@example.com"
    assert mailer.sent[0]["attachments"][0].filename == "a.txt"


class FakeSmtp:
    instances: list["FakeSmtp"] = []

    def __init__(self, host, port, timeout) -> None:
        self.host, self.port = host, port
        self.calls: list[tuple] = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.calls.append(("starttls",))

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.calls.append(("send", message))


def test_smtp_mailer_builds_a_multipart_message(monkeypatch) -> None:
    monkeypatch.setattr("src.adapters.smtp_mailer.smtplib.SMTP", FakeSmtp)
    FakeSmtp.instances.clear()
    mailer = SmtpMailer("mail.test", 587, "from@test", "user", "secret")
    mailer.send("to@test", "Subject", "Hello", [Attachment("d.json", b"{}", "application/json")])

    smtp = FakeSmtp.instances[0]
    assert (smtp.host, smtp.port) == ("mail.test", 587)
    assert smtp.calls[0] == ("starttls",)
    assert smtp.calls[1] == ("login", "user", "secret")
    message = message_from_bytes(smtp.calls[2][1].as_bytes())
    assert message["To"] == "to@test" and message["Subject"] == "Subject"
    parts = list(message.walk())
    assert any(p.get_filename() == "d.json" for p in parts)


def test_smtp_failure_becomes_mailer_error(monkeypatch) -> None:
    class Broken(FakeSmtp):
        def send_message(self, message):
            raise OSError("connection reset")

    monkeypatch.setattr("src.adapters.smtp_mailer.smtplib.SMTP", Broken)
    with pytest.raises(MailerError, match="connection reset"):
        SmtpMailer("mail.test", 25, "from@test", starttls=False).send("to", "s", "t", [])
