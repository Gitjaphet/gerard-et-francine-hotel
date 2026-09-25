from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.core.i18n import DEFAULT_LOCALE, Locale
from app.schemas.quote import StayQuoteRead
from app.schemas.room import RoomTypePublic
from app.services.quote import QuoteService
from app.services.room import RoomTypePublicService
from app.storage.base import Storage
from app.storage.deps import get_storage

router = APIRouter(prefix="/rooms", tags=["public"])


def get_room_public_service(
    db: DbSession, storage: Annotated[Storage, Depends(get_storage)]
) -> RoomTypePublicService:
    return RoomTypePublicService(db, storage)


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


def get_quote_service(db: DbSession) -> QuoteService:
    return QuoteService(db)


@router.get("/{slug}/quote")
async def quote_room(
    slug: str,
    check_in: Annotated[date, Query()],
    check_out: Annotated[date, Query()],
    service: Annotated[QuoteService, Depends(get_quote_service)],
    locale: LocaleQuery = DEFAULT_LOCALE,
) -> StayQuoteRead:
    return await service.quote_by_slug(locale, slug, check_in, check_out)
