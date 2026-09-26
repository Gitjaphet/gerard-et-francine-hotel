from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.booking import (
    BookingAssessment,
    BookingStatus,
    InvalidTransitionError,
    RoomCapacity,
    assess_booking,
    check_transition,
    whatsapp_url,
)
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.booking import BookingRequest
from app.models.user import User
from app.repositories.booking import BookingRequestRepository
from app.repositories.room import RoomTypeRepository
from app.schemas.booking import (
    BookingRequestAdminDetail,
    BookingRequestAdminRead,
    BookingRequestCreate,
)
from app.services.common import pick_translation
from app.services.quote import QuoteService, hotel_today


@dataclass(frozen=True)
class CreatedBooking:
    booking: BookingRequest
    assessment: BookingAssessment


class BookingRequestService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BookingRequestRepository(db)
        self.room_types = RoomTypeRepository(db)
        self.quotes = QuoteService(db)

    async def create(self, data: BookingRequestCreate) -> CreatedBooking:
        if data.website:
            raise BusinessRuleError("Demande invalide.")
        if data.check_in < hotel_today():
            raise BusinessRuleError("La date d'arrivée ne peut pas être dans le passé.")

        room_type = await self.room_types.get(data.room_type_id)
        if room_type is None or not room_type.is_active:
            raise NotFoundError("Chambre introuvable.")

        assessment = assess_booking(
            check_in=data.check_in,
            check_out=data.check_out,
            adults=data.adults,
            children=data.children,
            capacity=RoomCapacity(room_type.max_adults, room_type.max_children),
            base_price=room_type.base_price,
            seasons=await self.quotes.season_prices(room_type, data.check_in, data.check_out),
        )
        translation = pick_translation(room_type.translations, data.locale)

        booking = BookingRequest(
            room_type_id=room_type.id,
            room_name=translation.name if translation else f"#{room_type.id}",
            check_in=data.check_in,
            check_out=data.check_out,
            adults=data.adults,
            children=data.children,
            children_ages=data.children_ages,
            nights_count=assessment.nights_count,
            quoted_total=assessment.quoted_total,
            warnings=[warning.value for warning in assessment.warnings],
            guest_name=data.guest_name,
            email=str(data.email).lower(),
            phone=data.phone,
            prefers_whatsapp=data.prefers_whatsapp,
            locale=data.locale,
            message=data.message,
        )
        await self.repo.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        return CreatedBooking(booking, assessment)


class BookingAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BookingRequestRepository(db)

    async def list(self, status: BookingStatus | None = None) -> Sequence[BookingRequest]:
        return await self.repo.list(status=status)

    async def get(self, booking_id: int) -> BookingRequest:
        booking = await self.repo.get(booking_id)
        if booking is None:
            raise NotFoundError(f"Demande {booking_id} introuvable.")
        return booking

    async def detail(self, booking_id: int) -> BookingRequestAdminDetail:
        booking = await self.get(booking_id)
        overlapping = await self.repo.count_overlapping(booking, BookingStatus.CONFIRMED)
        return BookingRequestAdminDetail(
            **BookingRequestAdminRead.model_validate(booking).model_dump(),
            whatsapp_url=whatsapp_url(booking.phone),
            overlapping_confirmed=overlapping,
        )

    async def change_status(
        self, booking_id: int, target: BookingStatus, user: User
    ) -> BookingRequest:
        booking = await self.get(booking_id)
        try:
            check_transition(booking.status, target)
        except InvalidTransitionError as exc:
            raise ConflictError(str(exc)) from exc
        booking.status = target
        booking.handled_by_id = user.id
        booking.status_changed_at = datetime.now(UTC)
        return await self._save(booking)

    async def update_notes(self, booking_id: int, notes: str | None, user: User) -> BookingRequest:
        booking = await self.get(booking_id)
        booking.staff_notes = notes
        booking.handled_by_id = user.id
        return await self._save(booking)

    async def _save(self, booking: BookingRequest) -> BookingRequest:
        await self.db.commit()
        await self.db.refresh(booking)
        return booking
