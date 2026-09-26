from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.i18n import Locale
from app.core.pricing import PricingError, SeasonPrice, StayQuote, quote_stay
from app.models.room import RoomType
from app.repositories.room import RoomTypeRepository
from app.repositories.season import SeasonRepository
from app.schemas.quote import NightPriceRead, StayQuoteRead


def hotel_today() -> date:
    return datetime.now(ZoneInfo(get_settings().hotel_timezone)).date()


class QuoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.room_types = RoomTypeRepository(db)
        self.seasons = SeasonRepository(db)

    async def quote_by_slug(
        self, locale: Locale, slug: str, check_in: date, check_out: date
    ) -> StayQuoteRead:
        room_type = await self.room_types.get_active_by_slug(locale, slug)
        if room_type is None:
            raise NotFoundError("Chambre introuvable.")
        quote = await self.quote(room_type, check_in, check_out)
        return StayQuoteRead(
            check_in=check_in,
            check_out=check_out,
            nights_count=quote.nights_count,
            nights=[NightPriceRead(night=n.night, price=n.price) for n in quote.nights],
            total=quote.total,
        )

    async def quote(self, room_type: RoomType, check_in: date, check_out: date) -> StayQuote:
        if check_in < hotel_today():
            raise BusinessRuleError("La date d'arrivée ne peut pas être dans le passé.")

        season_prices = await self.season_prices(room_type, check_in, check_out)
        try:
            return quote_stay(check_in, check_out, room_type.base_price, season_prices)
        except PricingError as exc:
            raise BusinessRuleError(str(exc)) from exc

    async def season_prices(
        self, room_type: RoomType, check_in: date, check_out: date
    ) -> list[SeasonPrice]:
        """Les saisons qui touchent le séjour, vues depuis ce type de chambre."""
        last_night = max(check_in, check_out - timedelta(days=1))
        seasons = await self.seasons.list_overlapping(check_in, last_night)
        return [
            SeasonPrice(
                start_date=season.start_date,
                end_date=season.end_date,
                price=next((r.price for r in season.rates if r.room_type_id == room_type.id), None),
                min_nights=season.min_nights,
            )
            for season in seasons
        ]
