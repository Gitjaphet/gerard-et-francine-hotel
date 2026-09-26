from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError, TooManyAttemptsError
from app.core.i18n import Locale
from app.core.review import ReviewStatus
from app.core.security import hash_ip
from app.models.review import Review
from app.models.user import User
from app.repositories.review import ReviewRepository
from app.schemas.review import ReviewCreate, ReviewPage, ReviewPublic, ReviewSummary
from app.services.quote import hotel_today

MAX_REVIEWS_PER_IP = 3
REVIEW_WINDOW = timedelta(hours=24)


def summarize(distribution: dict[int, int]) -> ReviewSummary:
    count = sum(distribution.values())
    average = None
    if count:
        total = sum(rating * votes for rating, votes in distribution.items())
        average = (Decimal(total) / count).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return ReviewSummary(
        count=count,
        average=average,
        distribution={rating: distribution.get(rating, 0) for rating in range(5, 0, -1)},
    )


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReviewRepository(db)

    async def submit(self, data: ReviewCreate, ip_address: str) -> Review:
        if data.website:
            raise BusinessRuleError("Avis invalide.")
        if data.stayed_on and data.stayed_on > hotel_today():
            raise BusinessRuleError("La date de séjour ne peut pas être dans le futur.")

        ip_hash = hash_ip(ip_address)
        since = datetime.now(UTC) - REVIEW_WINDOW
        if await self.repo.count_since(ip_hash, since) >= MAX_REVIEWS_PER_IP:
            raise TooManyAttemptsError("Trop d'avis envoyés. Réessayez demain.")

        review = Review(
            **data.model_dump(exclude={"website", "email"}),
            email=str(data.email).lower(),
            ip_hash=ip_hash,
        )
        await self.repo.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def public_page(self, locale: Locale, page: int, page_size: int) -> ReviewPage:
        distribution = await self.repo.rating_distribution()
        reviews = await self.repo.list_approved(
            preferred_locale=locale, offset=(page - 1) * page_size, limit=page_size
        )
        return ReviewPage(
            items=[ReviewPublic.model_validate(review) for review in reviews],
            total=sum(distribution.values()),
            page=page,
            page_size=page_size,
        )

    async def summary(self) -> ReviewSummary:
        return summarize(await self.repo.rating_distribution())


class ReviewAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReviewRepository(db)

    async def list(self, status: ReviewStatus | None = None) -> Sequence[Review]:
        return await self.repo.list(status=status)

    async def get(self, review_id: int) -> Review:
        review = await self.repo.get(review_id)
        if review is None:
            raise NotFoundError(f"Avis {review_id} introuvable.")
        return review

    async def moderate(self, review_id: int, status: ReviewStatus, user: User) -> Review:
        review = await self.get(review_id)
        review.status = status
        review.moderated_by_id = user.id
        review.moderated_at = datetime.now(UTC)
        return await self._save(review)

    async def reply(self, review_id: int, text: str | None, user: User) -> Review:
        review = await self.get(review_id)
        review.owner_reply = text or None
        review.moderated_by_id = user.id
        return await self._save(review)

    async def delete(self, review_id: int) -> None:
        await self.repo.delete(await self.get(review_id))
        await self.db.commit()

    async def _save(self, review: Review) -> Review:
        await self.db.commit()
        await self.db.refresh(review)
        return review
