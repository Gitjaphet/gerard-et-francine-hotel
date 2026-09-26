from collections.abc import Sequence

from sqlalchemy import select
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
