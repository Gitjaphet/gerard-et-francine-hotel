from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import DbSession
from app.core.config import get_settings
from app.mail.base import Mailer
from app.mail.deps import get_mailer
from app.schemas.booking import BookingRequestCreate, BookingRequestReceipt
from app.services.booking import BookingRequestService
from app.services.notifications import booking_request_emails, send_safely

router = APIRouter(prefix="/booking-requests", tags=["public"])


def get_booking_service(db: DbSession) -> BookingRequestService:
    return BookingRequestService(db)


ServiceDep = Annotated[BookingRequestService, Depends(get_booking_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_booking_request(
    data: BookingRequestCreate,
    service: ServiceDep,
    background_tasks: BackgroundTasks,
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> BookingRequestReceipt:
    created = await service.create(data)
    booking = created.booking
    for email in booking_request_emails(
        booking,
        min_nights_required=created.assessment.min_nights_required,
        settings=get_settings(),
    ):
        background_tasks.add_task(send_safely, mailer, email)
    return BookingRequestReceipt(
        reference=booking.reference,
        status=booking.status,
        check_in=booking.check_in,
        check_out=booking.check_out,
        nights_count=booking.nights_count,
        quoted_total=booking.quoted_total,
        min_nights_required=created.assessment.min_nights_required,
        warnings=created.assessment.warnings,
    )
