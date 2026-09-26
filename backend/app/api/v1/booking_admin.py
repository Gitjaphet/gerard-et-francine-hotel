from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession
from app.core.booking import BookingStatus
from app.schemas.booking import (
    BookingNotesUpdate,
    BookingRequestAdminDetail,
    BookingRequestAdminRead,
    BookingStatusUpdate,
)
from app.services.booking import BookingAdminService

router = APIRouter(prefix="/admin/booking-requests", tags=["admin: bookings"])


def get_booking_admin_service(db: DbSession) -> BookingAdminService:
    return BookingAdminService(db)


ServiceDep = Annotated[BookingAdminService, Depends(get_booking_admin_service)]


@router.get("")
async def list_booking_requests(
    service: ServiceDep, status: Annotated[BookingStatus | None, Query()] = None
) -> list[BookingRequestAdminRead]:
    return [BookingRequestAdminRead.model_validate(b) for b in await service.list(status)]


@router.get("/{booking_id}")
async def read_booking_request(booking_id: int, service: ServiceDep) -> BookingRequestAdminDetail:
    return await service.detail(booking_id)


@router.post("/{booking_id}/status")
async def change_booking_status(
    booking_id: int, data: BookingStatusUpdate, user: CurrentUser, service: ServiceDep
) -> BookingRequestAdminRead:
    booking = await service.change_status(booking_id, data.status, user)
    return BookingRequestAdminRead.model_validate(booking)


@router.put("/{booking_id}/notes")
async def update_booking_notes(
    booking_id: int, data: BookingNotesUpdate, user: CurrentUser, service: ServiceDep
) -> BookingRequestAdminRead:
    booking = await service.update_notes(booking_id, data.staff_notes, user)
    return BookingRequestAdminRead.model_validate(booking)
