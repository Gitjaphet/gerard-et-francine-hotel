from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaAsset


class MediaAssetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> Sequence[MediaAsset]:
        result = await self.db.execute(select(MediaAsset).order_by(MediaAsset.id.desc()))
        return result.scalars().all()

    async def get(self, asset_id: int) -> MediaAsset | None:
        return await self.db.get(MediaAsset, asset_id)

    async def get_many(self, asset_ids: Sequence[int]) -> Sequence[MediaAsset]:
        if not asset_ids:
            return []
        result = await self.db.execute(select(MediaAsset).where(MediaAsset.id.in_(asset_ids)))
        return result.scalars().all()

    async def add(self, asset: MediaAsset) -> MediaAsset:
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def delete(self, asset: MediaAsset) -> None:
        await self.db.delete(asset)
        await self.db.flush()
