from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.hotel import SocialLinkRead, SocialLinkWrite
from app.services.hotel import SocialLinkService

router = APIRouter(prefix="/admin/social-links", tags=["admin: social links"])


def get_social_link_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SocialLinkService:
    return SocialLinkService(db)


ServiceDep = Annotated[SocialLinkService, Depends(get_social_link_service)]


@router.get("")
async def list_social_links(service: ServiceDep) -> list[SocialLinkRead]:
    links = await service.list()
    return [SocialLinkRead.model_validate(link) for link in links]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_social_link(data: SocialLinkWrite, service: ServiceDep) -> SocialLinkRead:
    link = await service.create(data)
    return SocialLinkRead.model_validate(link)


@router.put("/{link_id}")
async def update_social_link(
    link_id: int,
    data: SocialLinkWrite,
    service: ServiceDep,
) -> SocialLinkRead:
    link = await service.update(link_id, data)
    return SocialLinkRead.model_validate(link)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_social_link(link_id: int, service: ServiceDep) -> None:
    await service.delete(link_id)
