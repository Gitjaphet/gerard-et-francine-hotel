from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.core.pricing import MissingPriceError, SeasonPrice, quote_stay


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class BookingWarning(StrEnum):
    OVER_CAPACITY = "over_capacity"
    MIN_STAY_NOT_MET = "min_stay_not_met"
    PRICE_UNAVAILABLE = "price_unavailable"


# --- Évaluation d'une demande ----------------------------------------------------
# Logique pure : la demande n'est jamais refusée pour une règle de l'hôtel,
# les écarts deviennent des avertissements traités par la réception.


@dataclass(frozen=True)
class RoomCapacity:
    max_adults: int
    max_children: int


@dataclass(frozen=True)
class BookingAssessment:
    nights_count: int
    quoted_total: Decimal | None
    min_nights_required: int | None
    warnings: list[BookingWarning]


def assess_booking(
    *,
    check_in: date,
    check_out: date,
    adults: int,
    children: int,
    capacity: RoomCapacity,
    base_price: Decimal | None,
    seasons: Sequence[SeasonPrice],
) -> BookingAssessment:
    warnings: list[BookingWarning] = []

    if adults > capacity.max_adults or adults + children > (
        capacity.max_adults + capacity.max_children
    ):
        warnings.append(BookingWarning.OVER_CAPACITY)

    quoted_total: Decimal | None = None
    min_nights_required: int | None = None
    try:
        quote = quote_stay(check_in, check_out, base_price, seasons, enforce_min_stay=False)
    except MissingPriceError:
        warnings.append(BookingWarning.PRICE_UNAVAILABLE)
    else:
        quoted_total = quote.total
        min_nights_required = quote.min_nights_required
        if quote.nights_count < quote.min_nights_required:
            warnings.append(BookingWarning.MIN_STAY_NOT_MET)

    return BookingAssessment(
        nights_count=(check_out - check_in).days,
        quoted_total=quoted_total,
        min_nights_required=min_nights_required,
        warnings=warnings,
    )


# --- Transitions de statut -------------------------------------------------------

STATUS_LABELS: dict[BookingStatus, str] = {
    BookingStatus.PENDING: "en attente",
    BookingStatus.CONFIRMED: "confirmée",
    BookingStatus.DECLINED: "refusée",
    BookingStatus.CANCELLED: "annulée",
}

ALLOWED_TRANSITIONS: dict[BookingStatus, frozenset[BookingStatus]] = {
    BookingStatus.PENDING: frozenset(
        {BookingStatus.CONFIRMED, BookingStatus.DECLINED, BookingStatus.CANCELLED}
    ),
    BookingStatus.CONFIRMED: frozenset({BookingStatus.CANCELLED}),
    BookingStatus.DECLINED: frozenset(),
    BookingStatus.CANCELLED: frozenset(),
}


class InvalidTransitionError(ValueError):
    pass


def check_transition(current: BookingStatus, target: BookingStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(
            f"Une demande {STATUS_LABELS[current]} ne peut pas être {STATUS_LABELS[target]}."
        )


def whatsapp_url(phone: str | None) -> str | None:
    """Lien « cliquer pour discuter » : https://wa.me/ suivi des seuls chiffres du numéro."""
    if not phone:
        return None
    digits = "".join(char for char in phone if char.isdigit())
    return f"https://wa.me/{digits}" if len(digits) >= 6 else None
