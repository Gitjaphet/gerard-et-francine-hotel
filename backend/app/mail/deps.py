from functools import lru_cache

from app.core.config import get_settings
from app.mail.base import Mailer
from app.mail.console import ConsoleMailer
from app.mail.smtp import SmtpMailer


@lru_cache
def get_mailer() -> Mailer:
    settings = get_settings()
    if settings.email_backend == "smtp":
        return SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password.get_secret_value(),
            sender=settings.email_from,
            sender_name=settings.email_from_name,
        )
    return ConsoleMailer()
