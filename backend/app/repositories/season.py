from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.season import Season


class SeasonRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> Sequence[Season]:
        result = await self.db.execute(select(Season).order_by(Season.start_date))
        return result.scalars().all()

    async def get(self, season_id: int) -> Season | None:
        return await self.db.get(Season, season_id)

    async def list_overlapping(
        self, start: date, end: date, *, exclude_id: int | None = None
    ) -> Sequence[Season]:
        query = select(Season).where(Season.period.overlaps(Range(start, end, bounds="[]")))
        if exclude_id is not None:
            query = query.where(Season.id != exclude_id)
        result = await self.db.execute(query.order_by(Season.start_date))
        return result.scalars().all()

    async def add(self, season: Season) -> Season:
        self.db.add(season)
        await self.db.flush()
        return season

    async def delete(self, season: Season) -> None:
        await self.db.delete(season)
        await self.db.flush()
