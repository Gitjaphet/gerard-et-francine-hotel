from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status

from app.api.deps import DbSession
from app.core.config import get_settings
from app.schemas.media import MediaAssetRead, MediaTranslationsUpdate
from app.services.media import MediaService, to_media_read
from app.storage.base import Storage
from app.storage.deps import get_storage

router = APIRouter(prefix="/admin/media", tags=["admin: media"])


def get_media_service(
    db: DbSession, storage: Annotated[Storage, Depends(get_storage)]
) -> MediaService:
    return MediaService(db, storage)


ServiceDep = Annotated[MediaService, Depends(get_media_service)]


@router.get("")
async def list_media(service: ServiceDep) -> list[MediaAssetRead]:
    return [to_media_read(asset, service.storage) for asset in await service.list()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_media(file: UploadFile, service: ServiceDep) -> MediaAssetRead:
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    asset = await service.upload(file.filename or "image", data)
    return to_media_read(asset, service.storage)


@router.put("/{asset_id}/translations")
async def update_media_translations(
    asset_id: int, data: MediaTranslationsUpdate, service: ServiceDep
) -> MediaAssetRead:
    asset = await service.update_translations(asset_id, data.translations)
    return to_media_read(asset, service.storage)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(asset_id: int, service: ServiceDep) -> None:
    await service.delete(asset_id)
