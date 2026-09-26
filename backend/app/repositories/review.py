from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import Locale
from app.core.review import ReviewStatus
from app.models.review import Review


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, review: Review) -> Review:
        self.db.add(review)
        await self.db.flush()
        return review

    async def count_since(self, ip_hash: str, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Review)
            .where(Review.ip_hash == ip_hash, Review.created_at >= since)
        )
        return result.scalar_one()

    async def list_approved(
        self, *, preferred_locale: Locale, offset: int, limit: int
    ) -> Sequence[Review]:
        same_language_first = case((Review.locale == preferred_locale, 0), else_=1)
        result = await self.db.execute(
            select(Review)
            .where(Review.status == ReviewStatus.APPROVED)
            .order_by(same_language_first, Review.created_at.desc(), Review.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def rating_distribution(self) -> dict[int, int]:
        result = await self.db.execute(
            select(Review.rating, func.count())
            .where(Review.status == ReviewStatus.APPROVED)
            .group_by(Review.rating)
        )
        return dict(result.all())

    async def get(self, review_id: int) -> Review | None:
        return await self.db.get(Review, review_id)

    async def list(self, *, status: ReviewStatus | None = None) -> Sequence[Review]:
        query = select(Review).order_by(Review.created_at.desc(), Review.id.desc())
        if status is not None:
            query = query.where(Review.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete(self, review: Review) -> None:
        await self.db.delete(review)
        await self.db.flush()
