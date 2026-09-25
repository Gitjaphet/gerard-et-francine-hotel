from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.i18n import DEFAULT_LOCALE, Locale
from app.models.hotel import HotelSettings, HotelSettingsTranslation, SocialLink
from app.repositories.hotel import HotelSettingsRepository, SocialLinkRepository
from app.schemas.hotel import (
    HotelPublic,
    HotelPublicInfo,
    HotelSettingsTranslationRead,
    HotelSettingsTranslationWrite,
    HotelSettingsUpdate,
    SocialLinkPublic,
    SocialLinkWrite,
)


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


class SocialLinkService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SocialLinkRepository(db)

    async def list(self, *, active_only: bool = False) -> Sequence[SocialLink]:
        return await self.repo.list(active_only=active_only)

    async def get(self, link_id: int) -> SocialLink:
        link = await self.repo.get(link_id)
        if link is None:
            raise NotFoundError(f"Lien social {link_id} introuvable.")
        return link

    async def create(self, data: SocialLinkWrite) -> SocialLink:
        link = await self.repo.add(SocialLink(**data.model_dump()))
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def update(self, link_id: int, data: SocialLinkWrite) -> SocialLink:
        link = await self.get(link_id)
        for name, value in data.model_dump().items():
            setattr(link, name, value)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def delete(self, link_id: int) -> None:
        link = await self.get(link_id)
        await self.repo.delete(link)
        await self.db.commit()


class HotelPublicService:
    def __init__(self, db: AsyncSession) -> None:
        self.settings = HotelSettingsService(db)
        self.links = SocialLinkRepository(db)

    async def get(self, locale: Locale) -> HotelPublic:
        settings = await self.settings.get()
        links = await self.links.list(active_only=True)

        by_locale = {t.locale: t for t in settings.translations}
        translation = by_locale.get(locale) or by_locale.get(DEFAULT_LOCALE)
        texts = (
            HotelSettingsTranslationRead.model_validate(translation).model_dump(exclude={"locale"})
            if translation
            else {}
        )

        return HotelPublic(
            **HotelPublicInfo.model_validate(settings).model_dump(),
            **texts,
            locale=locale,
            content_locale=translation.locale if translation else DEFAULT_LOCALE,
            available_locales=[loc for loc in Locale if loc in by_locale],
            mga_rate=settings.eur_to_mga_rate if settings.show_mga_prices else None,
            social_links=[SocialLinkPublic.model_validate(link) for link in links],
        )
