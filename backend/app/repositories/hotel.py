from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hotel import HotelSettings, SocialLink


class HotelSettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self) -> HotelSettings | None:
        result = await self.db.execute(
            select(HotelSettings).order_by(HotelSettings.id).limit(1)
        )
        return result.scalar_one_or_none()

    async def add(self, settings: HotelSettings) -> HotelSettings:
        self.db.add(settings)
        await self.db.flush()
        return settings


class SocialLinkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, *, active_only: bool = False) -> Sequence[SocialLink]:
        query = select(SocialLink).order_by(SocialLink.position, SocialLink.id)
        if active_only:
            query = query.where(SocialLink.is_active.is_(True))
        result = await self.db.execute(query)
        return result.scalars().all()
