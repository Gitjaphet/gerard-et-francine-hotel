from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import DbSession, client_ip
from app.core.i18n import DEFAULT_LOCALE, Locale
from app.schemas.review import ReviewCreate, ReviewPage, ReviewReceipt, ReviewSummary
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["public"])


def get_review_service(db: DbSession) -> ReviewService:
    return ReviewService(db)


ServiceDep = Annotated[ReviewService, Depends(get_review_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_review(data: ReviewCreate, request: Request, service: ServiceDep) -> ReviewReceipt:
    await service.submit(data, client_ip(request))
    return ReviewReceipt()


@router.get("")
async def list_reviews(
    service: ServiceDep,
    locale: Annotated[Locale, Query()] = DEFAULT_LOCALE,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> ReviewPage:
    return await service.public_page(locale, page, page_size)


@router.get("/summary")
async def reviews_summary(service: ServiceDep) -> ReviewSummary:
    return await service.summary()
