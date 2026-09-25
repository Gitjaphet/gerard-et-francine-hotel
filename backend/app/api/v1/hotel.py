from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.hotel import HotelSettingsRead, HotelSettingsUpdate
from app.services.hotel import HotelSettingsService

router = APIRouter(prefix="/admin/hotel-settings", tags=["admin: hotel"])


def get_hotel_settings_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HotelSettingsService:
    return HotelSettingsService(db)


ServiceDep = Annotated[HotelSettingsService, Depends(get_hotel_settings_service)]


@router.get("")
async def read_hotel_settings(service: ServiceDep) -> HotelSettingsRead:
    settings = await service.get()
    return HotelSettingsRead.model_validate(settings)


@router.put("")
async def update_hotel_settings(
    data: HotelSettingsUpdate,
    service: ServiceDep,
) -> HotelSettingsRead:
    settings = await service.update(data)
    return HotelSettingsRead.model_validate(settings)
