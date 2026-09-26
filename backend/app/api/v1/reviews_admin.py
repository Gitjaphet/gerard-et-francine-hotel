from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.review import ReviewStatus
from app.schemas.review import ReviewAdminRead, ReviewModeration, ReviewReply
from app.services.review import ReviewAdminService

router = APIRouter(prefix="/admin/reviews", tags=["admin: reviews"])


def get_review_admin_service(db: DbSession) -> ReviewAdminService:
    return ReviewAdminService(db)


ServiceDep = Annotated[ReviewAdminService, Depends(get_review_admin_service)]


@router.get("")
async def list_reviews(
    service: ServiceDep, status: Annotated[ReviewStatus | None, Query()] = None
) -> list[ReviewAdminRead]:
    return [ReviewAdminRead.model_validate(review) for review in await service.list(status)]


@router.get("/{review_id}")
async def read_review(review_id: int, service: ServiceDep) -> ReviewAdminRead:
    return ReviewAdminRead.model_validate(await service.get(review_id))


@router.post("/{review_id}/moderation")
async def moderate_review(
    review_id: int, data: ReviewModeration, user: CurrentUser, service: ServiceDep
) -> ReviewAdminRead:
    return ReviewAdminRead.model_validate(await service.moderate(review_id, data.status, user))


@router.put("/{review_id}/reply")
async def reply_to_review(
    review_id: int, data: ReviewReply, user: CurrentUser, service: ServiceDep
) -> ReviewAdminRead:
    return ReviewAdminRead.model_validate(await service.reply(review_id, data.owner_reply, user))


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: int, service: ServiceDep) -> None:
    await service.delete(review_id)
