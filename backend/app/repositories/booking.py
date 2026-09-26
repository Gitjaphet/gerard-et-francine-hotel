from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.booking import BookingStatus
from app.models.booking import BookingRequest


class BookingRequestRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, booking_id: int) -> BookingRequest | None:
        return await self.db.get(BookingRequest, booking_id)

    async def list(self, *, status: BookingStatus | None = None) -> Sequence[BookingRequest]:
        query = select(BookingRequest).order_by(BookingRequest.created_at.desc())
        if status is not None:
            query = query.where(BookingRequest.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def add(self, booking: BookingRequest) -> BookingRequest:
        self.db.add(booking)
        await self.db.flush()
        return booking

    async def count_overlapping(self, booking: BookingRequest, status: BookingStatus) -> int:
        """Demandes du même type de chambre, dans ce statut, dont le séjour chevauche celui-ci."""
        if booking.room_type_id is None:
            return 0
        result = await self.db.execute(
            select(func.count())
            .select_from(BookingRequest)
            .where(
                BookingRequest.id != booking.id,
                BookingRequest.room_type_id == booking.room_type_id,
                BookingRequest.status == status,
                BookingRequest.check_in < booking.check_out,
                BookingRequest.check_out > booking.check_in,
            )
        )
        return result.scalar_one()
