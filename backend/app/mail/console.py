import logging

from app.mail.base import OutgoingEmail

logger = logging.getLogger(__name__)


class ConsoleMailer:
    """N'envoie rien : affiche l'email dans les journaux. Pour le développement."""

    async def send(self, email: OutgoingEmail) -> None:
        logger.info("Email (non envoyé) à %s — %s\n%s", email.to, email.subject, email.body)
