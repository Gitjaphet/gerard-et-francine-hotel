from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.hotel import HotelSettings, HotelSettingsTranslation
from app.repositories.hotel import HotelSettingsRepository
from app.schemas.hotel import HotelSettingsTranslationWrite, HotelSettingsUpdate


class HotelSettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = HotelSettingsRepository(db)

    async def get(self) -> HotelSettings:
        settings = await self.repo.get()
        if settings is None:
            raise NotFoundError("Les informations de l'hôtel ne sont pas encore configurées.")
        return settings

    async def update(self, data: HotelSettingsUpdate) -> HotelSettings:
        fields = data.model_dump(exclude={"translations"})
        settings = await self.repo.get()

        if settings is None:
            settings = await self.repo.add(HotelSettings(**fields, translations=[]))
        else:
            for name, value in fields.items():
                setattr(settings, name, value)

        self._sync_translations(settings, data.translations)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    @staticmethod
    def _sync_translations(
        settings: HotelSettings,
        translations: list[HotelSettingsTranslationWrite],
    ) -> None:
        existing = {t.locale: t for t in settings.translations}
        for item in translations:
            values = item.model_dump(exclude={"locale"})
            current = existing.get(item.locale)
            if current is None:
                settings.translations.append(HotelSettingsTranslation(locale=item.locale, **values))
            else:
                for name, value in values.items():
                    setattr(current, name, value)
