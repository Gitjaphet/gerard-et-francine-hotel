from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str
    reply_to: str | None = None


class Mailer(Protocol):
    """Contrat d'envoi : affichage en développement, SMTP en production."""

    async def send(self, email: OutgoingEmail) -> None: ...
