import asyncio
from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, InvalidFileError, NotFoundError
from app.core.images import InvalidImageError, ProcessedImage, process_image
from app.models.media import MediaAsset, MediaAssetTranslation
from app.repositories.media import MediaAssetRepository
from app.schemas.media import (
    MediaAssetRead,
    MediaTranslationRead,
    MediaTranslationWrite,
    MediaVariantRead,
)
from app.services.common import sync_translations
from app.storage.base import Storage


def variant_key(storage_key: str, variant: str) -> str:
    return f"{storage_key}/{variant}.webp"


def variant_urls(asset: MediaAsset, storage: Storage) -> dict[str, MediaVariantRead]:
    return {
        name: MediaVariantRead(url=storage.url(variant_key(asset.storage_key, name)), **size)
        for name, size in asset.variants.items()
    }


def to_media_read(asset: MediaAsset, storage: Storage) -> MediaAssetRead:
    return MediaAssetRead(
        id=asset.id,
        original_filename=asset.original_filename,
        width=asset.width,
        height=asset.height,
        variants=variant_urls(asset, storage),
        translations=[MediaTranslationRead.model_validate(t) for t in asset.translations],
    )


class MediaService:
    def __init__(self, db: AsyncSession, storage: Storage) -> None:
        self.db = db
        self.storage = storage
        self.repo = MediaAssetRepository(db)

    async def list(self) -> Sequence[MediaAsset]:
        return await self.repo.list()

    async def get(self, asset_id: int) -> MediaAsset:
        asset = await self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"Média {asset_id} introuvable.")
        return asset

    async def upload(self, filename: str, data: bytes) -> MediaAsset:
        max_bytes = get_settings().max_upload_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise FileTooLargeError(
                f"Fichier trop lourd : {get_settings().max_upload_mb} Mo maximum."
            )

        try:
            processed = await asyncio.to_thread(process_image, data)
        except InvalidImageError as exc:
            raise InvalidFileError(str(exc)) from exc

        storage_key = f"images/{uuid4().hex}"
        await self._save_variants(storage_key, processed)
        try:
            asset = MediaAsset(
                storage_key=storage_key,
                original_filename=filename[:255],
                width=processed.width,
                height=processed.height,
                variants={
                    v.name: {"width": v.width, "height": v.height} for v in processed.variants
                },
                translations=[],
            )
            await self.repo.add(asset)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            await self._delete_variants(storage_key, [v.name for v in processed.variants])
            raise
        await self.db.refresh(asset)
        return asset

    async def update_translations(
        self, asset_id: int, translations: Sequence[MediaTranslationWrite]
    ) -> MediaAsset:
        asset = await self.get(asset_id)
        sync_translations(asset.translations, translations, MediaAssetTranslation)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def delete(self, asset_id: int) -> None:
        asset = await self.get(asset_id)
        storage_key, names = asset.storage_key, list(asset.variants)
        await self.repo.delete(asset)
        await self.db.commit()
        await self._delete_variants(storage_key, names)

    async def _save_variants(self, storage_key: str, processed: ProcessedImage) -> None:
        await asyncio.gather(
            *(
                self.storage.save(variant_key(storage_key, v.name), v.content)
                for v in processed.variants
            )
        )

    async def _delete_variants(self, storage_key: str, names: Sequence[str]) -> None:
        await asyncio.gather(*(self.storage.delete(variant_key(storage_key, n)) for n in names))
