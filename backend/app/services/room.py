from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.i18n import Locale
from app.models.room import (
    Amenity,
    AmenityTranslation,
    RoomType,
    RoomTypePhoto,
    RoomTypeTranslation,
)
from app.repositories.media import MediaAssetRepository
from app.repositories.room import AmenityRepository, RoomTypeRepository
from app.schemas.room import (
    AmenityPublic,
    AmenityWrite,
    RoomPhotoPublic,
    RoomPhotoWrite,
    RoomTypeFields,
    RoomTypePublic,
    RoomTypeTextFields,
    RoomTypeTranslationWrite,
    RoomTypeWrite,
)
from app.services.common import pick_translation, sync_translations
from app.services.media import variant_urls
from app.storage.base import Storage

# Colonnes simples copiées du schema vers le modèle. Liste blanche : un champ ajouté
# au schema (relation, identifiants…) ne peut pas s'y glisser par accident.
ROOM_TYPE_COLUMNS = set(RoomTypeFields.model_fields)


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
        self.media = MediaAssetRepository(db)

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
            **data.model_dump(include=ROOM_TYPE_COLUMNS),
            translations=[],
            photos=[],
            amenities=list(await self._resolve_amenities(data.amenity_ids)),
        )
        await self._apply_photos(room_type, data.photos)
        sync_translations(room_type.translations, data.translations, RoomTypeTranslation)
        await self.repo.add(room_type)
        return await self._save(room_type)

    async def update(self, room_type_id: int, data: RoomTypeWrite) -> RoomType:
        room_type = await self.get(room_type_id)
        await self._ensure_slugs_available(data.translations, exclude_id=room_type_id)
        for name, value in data.model_dump(include=ROOM_TYPE_COLUMNS).items():
            setattr(room_type, name, value)
        room_type.amenities = list(await self._resolve_amenities(data.amenity_ids))
        await self._apply_photos(room_type, data.photos)
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
        return amenities

    async def _apply_photos(self, room_type: RoomType, photos: Sequence[RoomPhotoWrite]) -> None:
        asset_ids = [photo.media_asset_id for photo in photos]
        found = {asset.id for asset in await self.media.get_many(asset_ids)}
        missing = set(asset_ids) - found
        if missing:
            ids = ", ".join(str(asset_id) for asset_id in sorted(missing))
            raise NotFoundError(f"Photo(s) introuvable(s) : {ids}.")

        # L'index unique partiel refuse deux couvertures, même un instant pendant l'écriture :
        # on retire d'abord les couvertures existantes, puis on pose la nouvelle.
        if any(photo.is_cover for photo in room_type.photos):
            for photo in room_type.photos:
                photo.is_cover = False
            await self.db.flush()

        existing = {photo.media_asset_id: photo for photo in room_type.photos}
        updated: list[RoomTypePhoto] = []
        for position, item in enumerate(photos):
            photo = existing.get(item.media_asset_id) or RoomTypePhoto(
                media_asset_id=item.media_asset_id
            )
            photo.position = position
            photo.is_cover = item.is_cover
            updated.append(photo)
        room_type.photos = updated

    async def _save(self, room_type: RoomType) -> RoomType:
        await self.db.commit()
        await self.db.refresh(room_type)
        return room_type


class RoomTypePublicService:
    def __init__(self, db: AsyncSession, storage: Storage) -> None:
        self.repo = RoomTypeRepository(db)
        self.storage = storage

    async def list(self, locale: Locale) -> list[RoomTypePublic]:
        room_types = await self.repo.list(active_only=True)
        return [self._to_public(room_type, locale) for room_type in room_types]

    async def get_by_slug(self, locale: Locale, slug: str) -> RoomTypePublic:
        room_type = await self.repo.get_active_by_slug(locale, slug)
        if room_type is None:
            raise NotFoundError("Chambre introuvable.")
        return self._to_public(room_type, locale)

    def _to_public(self, room_type: RoomType, locale: Locale) -> RoomTypePublic:
        translation = pick_translation(room_type.translations, locale)
        if translation is None:
            raise NotFoundError("Chambre introuvable.")

        amenities = []
        for amenity in room_type.amenities:
            amenity_translation = pick_translation(amenity.translations, locale)
            name = amenity_translation.name if amenity_translation else amenity.code
            amenities.append(AmenityPublic(code=amenity.code, icon=amenity.icon, name=name))

        photos = []
        for photo in room_type.photos:
            asset = photo.media_asset
            alt_texts = {t.locale: t.alt_text for t in asset.translations}
            photos.append(
                RoomPhotoPublic(
                    alt=alt_texts.get(locale) or translation.name,
                    width=asset.width,
                    height=asset.height,
                    is_cover=photo.is_cover,
                    variants=variant_urls(asset, self.storage),
                )
            )

        texts = RoomTypeTextFields.model_validate(translation, from_attributes=True)
        return RoomTypePublic(
            **texts.model_dump(),
            id=room_type.id,
            slug=translation.slug,
            locale=locale,
            content_locale=translation.locale,
            slugs={t.locale: t.slug for t in room_type.translations},
            max_adults=room_type.max_adults,
            max_children=room_type.max_children,
            size_m2=room_type.size_m2,
            amenities=amenities,
            photos=photos,
        )
