"""Calcul du prix d'un séjour. Logique pure : aucune dépendance à la base ou à l'API."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

MAX_NIGHTS = 60


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class SeasonPrice:
    """Une saison vue depuis un type de chambre donné. Dates incluses."""

    start_date: date
    end_date: date
    price: Decimal | None
    min_nights: int | None = None

    def covers(self, night: date) -> bool:
        return self.start_date <= night <= self.end_date


@dataclass(frozen=True)
class NightPrice:
    night: date
    price: Decimal


@dataclass(frozen=True)
class StayQuote:
    nights: list[NightPrice]
    total: Decimal

    @property
    def nights_count(self) -> int:
        return len(self.nights)


def quote_stay(
    check_in: date,
    check_out: date,
    base_price: Decimal | None,
    seasons: Sequence[SeasonPrice],
) -> StayQuote:
    nights_count = (check_out - check_in).days
    if nights_count < 1:
        raise PricingError("La date de départ doit être postérieure à la date d'arrivée.")
    if nights_count > MAX_NIGHTS:
        raise PricingError(f"Un séjour ne peut pas dépasser {MAX_NIGHTS} nuits.")

    nights: list[NightPrice] = []
    required_nights = 1
    for offset in range(nights_count):
        night = check_in + timedelta(days=offset)
        season = next((s for s in seasons if s.covers(night)), None)

        price = season.price if season and season.price is not None else base_price
        if price is None:
            raise PricingError(f"Aucun tarif n'est défini pour la nuit du {night:%d/%m/%Y}.")
        if season and season.min_nights:
            required_nights = max(required_nights, season.min_nights)
        nights.append(NightPrice(night, price))

    if nights_count < required_nights:
        raise PricingError(f"Séjour minimum de {required_nights} nuits sur ces dates.")

    return StayQuote(nights=nights, total=sum((n.price for n in nights), Decimal("0")))
