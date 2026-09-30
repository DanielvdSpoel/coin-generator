from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    media_type: str


class Mailer(ABC):
    """Sends one email. The only outbound action the backend performs (decision D19)."""

    @abstractmethod
    def send(self, to: str, subject: str, text: str, attachments: list[Attachment]) -> None:
        """Deliver the message or raise ``MailerError``."""
