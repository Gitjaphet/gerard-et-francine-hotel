from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession
from app.schemas.season import SeasonRead, SeasonWrite
from app.services.season import SeasonService

router = APIRouter(prefix="/admin/seasons", tags=["admin: rates"])


def get_season_service(db: DbSession) -> SeasonService:
    return SeasonService(db)


ServiceDep = Annotated[SeasonService, Depends(get_season_service)]


@router.get("")
async def list_seasons(service: ServiceDep) -> list[SeasonRead]:
    return [SeasonRead.model_validate(season) for season in await service.list()]


@router.get("/{season_id}")
async def read_season(season_id: int, service: ServiceDep) -> SeasonRead:
    return SeasonRead.model_validate(await service.get(season_id))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_season(data: SeasonWrite, service: ServiceDep) -> SeasonRead:
    return SeasonRead.model_validate(await service.create(data))


@router.put("/{season_id}")
async def update_season(season_id: int, data: SeasonWrite, service: ServiceDep) -> SeasonRead:
    return SeasonRead.model_validate(await service.update(season_id, data))


@router.delete("/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_season(season_id: int, service: ServiceDep) -> None:
    await service.delete(season_id)
