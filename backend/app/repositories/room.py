from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import Locale
from app.models.room import Amenity, RoomType, RoomTypeTranslation


class AmenityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> Sequence[Amenity]:
        result = await self.db.execute(select(Amenity).order_by(Amenity.position, Amenity.id))
        return result.scalars().all()

    async def get(self, amenity_id: int) -> Amenity | None:
        return await self.db.get(Amenity, amenity_id)

    async def get_many(self, amenity_ids: Sequence[int]) -> Sequence[Amenity]:
        if not amenity_ids:
            return []
        result = await self.db.execute(select(Amenity).where(Amenity.id.in_(amenity_ids)))
        return result.scalars().all()

    async def code_exists(self, code: str, *, exclude_id: int | None = None) -> bool:
        condition = Amenity.code == code
        if exclude_id is not None:
            condition = condition & (Amenity.id != exclude_id)
        result = await self.db.execute(select(exists().where(condition)))
        return bool(result.scalar())

    async def add(self, amenity: Amenity) -> Amenity:
        self.db.add(amenity)
        await self.db.flush()
        return amenity

    async def delete(self, amenity: Amenity) -> None:
        await self.db.delete(amenity)
        await self.db.flush()


class RoomTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, *, active_only: bool = False) -> Sequence[RoomType]:
        query = select(RoomType).order_by(RoomType.position, RoomType.id)
        if active_only:
            query = query.where(RoomType.is_active.is_(True))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get(self, room_type_id: int) -> RoomType | None:
        return await self.db.get(RoomType, room_type_id)

    async def get_many(self, room_type_ids: Sequence[int]) -> Sequence[RoomType]:
        if not room_type_ids:
            return []
        result = await self.db.execute(select(RoomType).where(RoomType.id.in_(room_type_ids)))
        return result.scalars().all()

    async def get_active_by_slug(self, locale: Locale, slug: str) -> RoomType | None:
        result = await self.db.execute(
            select(RoomType)
            .join(RoomType.translations)
            .where(
                RoomTypeTranslation.locale == locale,
                RoomTypeTranslation.slug == slug,
                RoomType.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def slug_exists(
        self, locale: Locale, slug: str, *, exclude_room_type_id: int | None = None
    ) -> bool:
        condition = (RoomTypeTranslation.locale == locale) & (RoomTypeTranslation.slug == slug)
        if exclude_room_type_id is not None:
            condition = condition & (RoomTypeTranslation.room_type_id != exclude_room_type_id)
        result = await self.db.execute(select(exists().where(condition)))
        return bool(result.scalar())

    async def add(self, room_type: RoomType) -> RoomType:
        self.db.add(room_type)
        await self.db.flush()
        return room_type

    async def delete(self, room_type: RoomType) -> None:
        await self.db.delete(room_type)
        await self.db.flush()
