from datetime import date
from decimal import Decimal

import pytest

from app.core.pricing import PricingError, SeasonPrice, quote_stay

HIGH_SEASON = SeasonPrice(date(2026, 7, 1), date(2026, 10, 31), Decimal("65.00"))
NO_RATE_SEASON = SeasonPrice(date(2026, 11, 1), date(2026, 11, 30), None)
HOLIDAYS = SeasonPrice(date(2026, 12, 20), date(2027, 1, 5), Decimal("80.00"), min_nights=5)
SEASONS = [HIGH_SEASON, NO_RATE_SEASON, HOLIDAYS]
BASE = Decimal("45.00")


def test_departure_day_is_not_charged() -> None:
    quote = quote_stay(date(2026, 3, 10), date(2026, 3, 13), BASE, SEASONS)

    assert quote.nights_count == 3
    assert [n.night.day for n in quote.nights] == [10, 11, 12]
    assert quote.total == Decimal("135.00")


def test_each_night_uses_the_price_of_its_own_season() -> None:
    quote = quote_stay(date(2026, 6, 29), date(2026, 7, 2), BASE, SEASONS)

    assert [n.price for n in quote.nights] == [Decimal("45.00"), Decimal("45.00"), Decimal("65.00")]
    assert quote.total == Decimal("155.00")


def test_season_without_rate_for_this_room_falls_back_to_base_price() -> None:
    quote = quote_stay(date(2026, 11, 10), date(2026, 11, 12), BASE, SEASONS)

    assert quote.total == Decimal("90.00")


def test_decimal_amounts_stay_exact() -> None:
    quote = quote_stay(date(2026, 3, 1), date(2026, 3, 4), Decimal("45.10"), [])

    assert quote.total == Decimal("135.30")


def test_missing_price_is_reported_with_the_night_concerned() -> None:
    with pytest.raises(PricingError, match="10/11/2026"):
        quote_stay(date(2026, 11, 10), date(2026, 11, 12), None, SEASONS)


def test_minimum_stay_of_a_season_is_enforced() -> None:
    with pytest.raises(PricingError, match="minimum de 5 nuits"):
        quote_stay(date(2026, 12, 18), date(2026, 12, 22), BASE, SEASONS)


def test_minimum_stay_is_satisfied_by_a_long_enough_stay() -> None:
    quote = quote_stay(date(2026, 12, 18), date(2026, 12, 25), BASE, SEASONS)

    assert quote.total == Decimal("45.00") * 2 + Decimal("80.00") * 5


@pytest.mark.parametrize(
    ("check_in", "check_out"),
    [(date(2026, 3, 10), date(2026, 3, 10)), (date(2026, 3, 10), date(2026, 3, 9))],
)
def test_departure_must_be_after_arrival(check_in: date, check_out: date) -> None:
    with pytest.raises(PricingError, match="postérieure"):
        quote_stay(check_in, check_out, BASE, SEASONS)


def test_stays_longer_than_the_maximum_are_rejected() -> None:
    with pytest.raises(PricingError, match="60 nuits"):
        quote_stay(date(2026, 1, 1), date(2026, 3, 15), BASE, [])
