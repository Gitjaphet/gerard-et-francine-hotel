from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.room import Amenity, AmenityTranslation, RoomType, RoomTypeTranslation
from app.repositories.room import AmenityRepository, RoomTypeRepository
from app.schemas.room import AmenityWrite, RoomTypeTranslationWrite, RoomTypeWrite
from app.services.common import sync_translations


class AmenityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AmenityRepository(db)

    async def list(self) -> Sequence[Amenity]:
        return await self.repo.list()

    async def get(self, amenity_id: int) -> Amenity:
        amenity = await self.repo.get(amenity_id)
        if amenity is None:
            raise NotFoundError(f"Équipement {amenity_id} introuvable.")
        return amenity

    async def create(self, data: AmenityWrite) -> Amenity:
        await self._ensure_code_available(data.code)
        amenity = Amenity(**data.model_dump(exclude={"translations"}), translations=[])
        sync_translations(amenity.translations, data.translations, AmenityTranslation)
        await self.repo.add(amenity)
        return await self._save(amenity)

    async def update(self, amenity_id: int, data: AmenityWrite) -> Amenity:
        amenity = await self.get(amenity_id)
        await self._ensure_code_available(data.code, exclude_id=amenity_id)
        for name, value in data.model_dump(exclude={"translations"}).items():
            setattr(amenity, name, value)
        sync_translations(amenity.translations, data.translations, AmenityTranslation)
        return await self._save(amenity)

    async def delete(self, amenity_id: int) -> None:
        await self.repo.delete(await self.get(amenity_id))
        await self.db.commit()

    async def _ensure_code_available(self, code: str, *, exclude_id: int | None = None) -> None:
        if await self.repo.code_exists(code, exclude_id=exclude_id):
            raise ConflictError(f"Le code d'équipement « {code} » est déjà utilisé.")

    async def _save(self, amenity: Amenity) -> Amenity:
        await self.db.commit()
        await self.db.refresh(amenity)
        return amenity


class RoomTypeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RoomTypeRepository(db)
        self.amenities = AmenityRepository(db)

    async def list(self) -> Sequence[RoomType]:
        return await self.repo.list()

    async def get(self, room_type_id: int) -> RoomType:
        room_type = await self.repo.get(room_type_id)
        if room_type is None:
            raise NotFoundError(f"Type de chambre {room_type_id} introuvable.")
        return room_type

    async def create(self, data: RoomTypeWrite) -> RoomType:
        await self._ensure_slugs_available(data.translations)
        room_type = RoomType(
            **data.model_dump(exclude={"translations", "amenity_ids"}),
            translations=[],
            amenities=list(await self._resolve_amenities(data.amenity_ids)),
        )
        sync_translations(room_type.translations, data.translations, RoomTypeTranslation)
        await self.repo.add(room_type)
        return await self._save(room_type)

    async def update(self, room_type_id: int, data: RoomTypeWrite) -> RoomType:
        room_type = await self.get(room_type_id)
        await self._ensure_slugs_available(data.translations, exclude_id=room_type_id)
        for name, value in data.model_dump(exclude={"translations", "amenity_ids"}).items():
            setattr(room_type, name, value)
        room_type.amenities = list(await self._resolve_amenities(data.amenity_ids))
        sync_translations(room_type.translations, data.translations, RoomTypeTranslation)
        return await self._save(room_type)

    async def delete(self, room_type_id: int) -> None:
        await self.repo.delete(await self.get(room_type_id))
        await self.db.commit()

    async def _ensure_slugs_available(
        self,
        translations: Sequence[RoomTypeTranslationWrite],
        *,
        exclude_id: int | None = None,
    ) -> None:
        for translation in translations:
            slug = translation.slug or ""
            if await self.repo.slug_exists(
                translation.locale, slug, exclude_room_type_id=exclude_id
            ):
                raise ConflictError(
                    f"L'adresse « {slug} » est déjà utilisée en « {translation.locale.value} »."
                )

    async def _resolve_amenities(self, amenity_ids: Sequence[int]) -> Sequence[Amenity]:
        amenities = await self.amenities.get_many(amenity_ids)
        missing = set(amenity_ids) - {amenity.id for amenity in amenities}
        if missing:
            ids = ", ".join(str(amenity_id) for amenity_id in sorted(missing))
            raise NotFoundError(f"Équipement(s) introuvable(s) : {ids}.")
        order = {amenity_id: index for index, amenity_id in enumerate(amenity_ids)}
        return sorted(amenities, key=lambda amenity: order[amenity.id])

    async def _save(self, room_type: RoomType) -> RoomType:
        await self.db.commit()
        await self.db.refresh(room_type)
        return room_type
