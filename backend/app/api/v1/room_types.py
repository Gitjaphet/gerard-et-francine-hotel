from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession
from app.schemas.room import RoomTypeRead, RoomTypeWrite
from app.services.room import RoomTypeService

router = APIRouter(prefix="/admin/room-types", tags=["admin: rooms"])


def get_room_type_service(db: DbSession) -> RoomTypeService:
    return RoomTypeService(db)


ServiceDep = Annotated[RoomTypeService, Depends(get_room_type_service)]


@router.get("")
async def list_room_types(service: ServiceDep) -> list[RoomTypeRead]:
    return [RoomTypeRead.model_validate(room_type) for room_type in await service.list()]


@router.get("/{room_type_id}")
async def read_room_type(room_type_id: int, service: ServiceDep) -> RoomTypeRead:
    return RoomTypeRead.model_validate(await service.get(room_type_id))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_room_type(data: RoomTypeWrite, service: ServiceDep) -> RoomTypeRead:
    return RoomTypeRead.model_validate(await service.create(data))


@router.put("/{room_type_id}")
async def update_room_type(
    room_type_id: int, data: RoomTypeWrite, service: ServiceDep
) -> RoomTypeRead:
    return RoomTypeRead.model_validate(await service.update(room_type_id, data))


@router.delete("/{room_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_type(room_type_id: int, service: ServiceDep) -> None:
    await service.delete(room_type_id)
