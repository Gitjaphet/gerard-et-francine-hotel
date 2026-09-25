from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession
from app.schemas.room import AmenityRead, AmenityWrite
from app.services.room import AmenityService

router = APIRouter(prefix="/admin/amenities", tags=["admin: rooms"])


def get_amenity_service(db: DbSession) -> AmenityService:
    return AmenityService(db)


ServiceDep = Annotated[AmenityService, Depends(get_amenity_service)]


@router.get("")
async def list_amenities(service: ServiceDep) -> list[AmenityRead]:
    return [AmenityRead.model_validate(amenity) for amenity in await service.list()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_amenity(data: AmenityWrite, service: ServiceDep) -> AmenityRead:
    return AmenityRead.model_validate(await service.create(data))


@router.put("/{amenity_id}")
async def update_amenity(amenity_id: int, data: AmenityWrite, service: ServiceDep) -> AmenityRead:
    return AmenityRead.model_validate(await service.update(amenity_id, data))


@router.delete("/{amenity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_amenity(amenity_id: int, service: ServiceDep) -> None:
    await service.delete(amenity_id)
