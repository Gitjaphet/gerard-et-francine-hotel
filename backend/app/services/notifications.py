import logging

from app.core.config import Settings
from app.mail.base import Mailer, OutgoingEmail
from app.mail.templates import guest_acknowledgement, reception_alert
from app.models.booking import BookingRequest

logger = logging.getLogger(__name__)


def booking_request_emails(
    booking: BookingRequest, *, min_nights_required: int | None, settings: Settings
) -> list[OutgoingEmail]:
    emails = [guest_acknowledgement(booking, min_nights_required=min_nights_required)]
    if settings.reception_email:
        emails.append(
            reception_alert(
                booking,
                reception_email=settings.reception_email,
                admin_base_url=settings.admin_base_url,
            )
        )
    return emails


async def send_safely(mailer: Mailer, email: OutgoingEmail) -> None:
    """Un email qui échoue est journalisé, jamais propagé : la demande est déjà enregistrée."""
    try:
        await mailer.send(email)
    except Exception:
        logger.exception("Échec de l'envoi de l'email « %s » à %s", email.subject, email.to)
