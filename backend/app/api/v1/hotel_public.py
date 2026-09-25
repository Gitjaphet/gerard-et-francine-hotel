from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import DEFAULT_LOCALE, Locale
from app.db.session import get_db
from app.schemas.hotel import HotelPublic
from app.services.hotel import HotelPublicService

router = APIRouter(prefix="/hotel", tags=["public"])


def get_hotel_public_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HotelPublicService:
    return HotelPublicService(db)


@router.get("")
async def read_hotel(
    service: Annotated[HotelPublicService, Depends(get_hotel_public_service)],
    locale: Annotated[Locale, Query()] = DEFAULT_LOCALE,
) -> HotelPublic:
    return await service.get(locale)
