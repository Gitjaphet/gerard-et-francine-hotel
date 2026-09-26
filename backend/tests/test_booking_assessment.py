from datetime import date
from decimal import Decimal

import pytest

from app.core.booking import BookingWarning, RoomCapacity, assess_booking
from app.core.pricing import PricingError, SeasonPrice

DOUBLE_ROOM = RoomCapacity(max_adults=2, max_children=1)
HOLIDAYS = SeasonPrice(date(2027, 12, 20), date(2028, 1, 5), Decimal("80.00"), min_nights=5)


def assess(**overrides: object) -> object:
    params: dict[str, object] = {
        "check_in": date(2027, 3, 10),
        "check_out": date(2027, 3, 13),
        "adults": 2,
        "children": 0,
        "capacity": DOUBLE_ROOM,
        "base_price": Decimal("45.00"),
        "seasons": [HOLIDAYS],
        **overrides,
    }
    return assess_booking(**params)  # type: ignore[arg-type]


def test_regular_request_has_price_and_no_warning() -> None:
    result = assess()

    assert result.quoted_total == Decimal("135.00")  # type: ignore[attr-defined]
    assert result.nights_count == 3  # type: ignore[attr-defined]
    assert result.warnings == []  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("adults", "children", "over_capacity"),
    [(2, 1, False), (1, 2, False), (3, 0, True), (2, 2, True)],
    ids=["full-room", "child-uses-adult-bed", "too-many-adults", "too-many-guests"],
)
def test_capacity_is_flagged_but_never_blocking(
    adults: int, children: int, over_capacity: bool
) -> None:
    result = assess(adults=adults, children=children)

    assert (BookingWarning.OVER_CAPACITY in result.warnings) is over_capacity  # type: ignore[attr-defined]
    assert result.quoted_total == Decimal("135.00")  # type: ignore[attr-defined]


def test_short_stay_keeps_its_price_and_is_flagged() -> None:
    result = assess(check_in=date(2027, 12, 22), check_out=date(2027, 12, 24))

    assert result.warnings == [BookingWarning.MIN_STAY_NOT_MET]  # type: ignore[attr-defined]
    assert result.quoted_total == Decimal("160.00")  # type: ignore[attr-defined]
    assert result.min_nights_required == 5  # type: ignore[attr-defined]


def test_missing_price_is_flagged_without_total() -> None:
    result = assess(base_price=None)

    assert result.warnings == [BookingWarning.PRICE_UNAVAILABLE]  # type: ignore[attr-defined]
    assert result.quoted_total is None  # type: ignore[attr-defined]


def test_several_warnings_can_be_combined() -> None:
    result = assess(adults=4, base_price=None)

    assert result.warnings == [  # type: ignore[attr-defined]
        BookingWarning.OVER_CAPACITY,
        BookingWarning.PRICE_UNAVAILABLE,
    ]


def test_impossible_dates_are_still_rejected() -> None:
    with pytest.raises(PricingError, match="postérieure"):
        assess(check_out=date(2027, 3, 10))
