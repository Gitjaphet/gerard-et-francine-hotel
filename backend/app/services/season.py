from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.i18n import DEFAULT_LOCALE
from app.models.season import Season, SeasonRate, SeasonTranslation
from app.repositories.room import RoomTypeRepository
from app.repositories.season import SeasonRepository
from app.schemas.season import SeasonFields, SeasonRateWrite, SeasonWrite
from app.services.common import pick_translation, sync_translations

SEASON_COLUMNS = set(SeasonFields.model_fields)
OVERLAP_CONSTRAINT = "ex_season_no_overlap"
OVERLAP_MESSAGE = "Cette période chevauche une autre saison."


class SeasonService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SeasonRepository(db)
        self.room_types = RoomTypeRepository(db)

    async def list(self) -> Sequence[Season]:
        return await self.repo.list()

    async def get(self, season_id: int) -> Season:
        season = await self.repo.get(season_id)
        if season is None:
            raise NotFoundError(f"Saison {season_id} introuvable.")
        return season

    async def create(self, data: SeasonWrite) -> Season:
        await self._ensure_no_overlap(data)
        async with self._overlap_guard():
            season = Season(**data.model_dump(include=SEASON_COLUMNS), translations=[], rates=[])
            await self._apply_rates(season, data.rates)
            sync_translations(season.translations, data.translations, SeasonTranslation)
            await self.repo.add(season)
            await self.db.commit()
        await self.db.refresh(season)
        return season

    async def update(self, season_id: int, data: SeasonWrite) -> Season:
        season = await self.get(season_id)
        await self._ensure_no_overlap(data, exclude_id=season_id)
        async with self._overlap_guard():
            for name, value in data.model_dump(include=SEASON_COLUMNS).items():
                setattr(season, name, value)
            await self._apply_rates(season, data.rates)
            sync_translations(season.translations, data.translations, SeasonTranslation)
            await self.db.commit()
        await self.db.refresh(season)
        return season

    async def delete(self, season_id: int) -> None:
        await self.repo.delete(await self.get(season_id))
        await self.db.commit()

    @asynccontextmanager
    async def _overlap_guard(self) -> AsyncIterator[None]:
        """Traduit la contrainte d'exclusion en 409, où qu'elle se déclenche dans le bloc.

        Le SQL part dès le premier flush (explicite ou automatique avant une requête),
        pas seulement au commit : c'est tout le bloc d'écriture qu'il faut protéger.
        """
        try:
            yield
        except IntegrityError as exc:
            await self.db.rollback()
            if OVERLAP_CONSTRAINT in str(exc.orig):
                raise ConflictError(OVERLAP_MESSAGE) from exc
            raise

    async def _ensure_no_overlap(self, data: SeasonWrite, *, exclude_id: int | None = None) -> None:
        overlapping = await self.repo.list_overlapping(
            data.start_date, data.end_date, exclude_id=exclude_id
        )
        if overlapping:
            other = overlapping[0]
            translation = pick_translation(other.translations, DEFAULT_LOCALE)
            name = translation.name if translation else f"#{other.id}"
            raise ConflictError(
                f"Cette période chevauche la saison « {name} » "
                f"(du {other.start_date:%d/%m/%Y} au {other.end_date:%d/%m/%Y})."
            )

    async def _apply_rates(self, season: Season, rates: Sequence[SeasonRateWrite]) -> None:
        requested = [rate.room_type_id for rate in rates]
        found = {room_type.id for room_type in await self.room_types.get_many(requested)}
        missing = set(requested) - found
        if missing:
            ids = ", ".join(str(room_type_id) for room_type_id in sorted(missing))
            raise NotFoundError(f"Type(s) de chambre introuvable(s) : {ids}.")

        existing = {rate.room_type_id: rate for rate in season.rates}
        updated: list[SeasonRate] = []
        for item in rates:
            rate = existing.get(item.room_type_id) or SeasonRate(room_type_id=item.room_type_id)
            rate.price = item.price
            updated.append(rate)
        season.rates = updated
