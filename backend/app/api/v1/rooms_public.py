from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.core.i18n import DEFAULT_LOCALE, Locale
from app.schemas.room import RoomTypePublic
from app.services.room import RoomTypePublicService

router = APIRouter(prefix="/rooms", tags=["public"])


def get_room_public_service(db: DbSession) -> RoomTypePublicService:
    return RoomTypePublicService(db)


ServiceDep = Annotated[RoomTypePublicService, Depends(get_room_public_service)]
LocaleQuery = Annotated[Locale, Query()]


@router.get("")
async def list_rooms(
    service: ServiceDep, locale: LocaleQuery = DEFAULT_LOCALE
) -> list[RoomTypePublic]:
    return await service.list(locale)


@router.get("/{slug}")
async def read_room(
    slug: str, service: ServiceDep, locale: LocaleQuery = DEFAULT_LOCALE
) -> RoomTypePublic:
    return await service.get_by_slug(locale, slug)
