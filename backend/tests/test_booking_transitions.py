import pytest

from app.core.booking import (
    ALLOWED_TRANSITIONS,
    STATUS_LABELS,
    BookingStatus,
    InvalidTransitionError,
    check_transition,
)

ALLOWED = {
    (BookingStatus.PENDING, BookingStatus.CONFIRMED),
    (BookingStatus.PENDING, BookingStatus.DECLINED),
    (BookingStatus.PENDING, BookingStatus.CANCELLED),
    (BookingStatus.CONFIRMED, BookingStatus.CANCELLED),
}
ALL_PAIRS = [(current, target) for current in BookingStatus for target in BookingStatus]


@pytest.mark.parametrize(("current", "target"), sorted(ALLOWED))
def test_allowed_transitions_pass(current: BookingStatus, target: BookingStatus) -> None:
    check_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"), sorted(pair for pair in ALL_PAIRS if pair not in ALLOWED)
)
def test_every_other_transition_is_rejected(current: BookingStatus, target: BookingStatus) -> None:
    with pytest.raises(InvalidTransitionError):
        check_transition(current, target)


def test_error_message_is_readable() -> None:
    with pytest.raises(
        InvalidTransitionError, match="Une demande refusée ne peut pas être confirmée"
    ):
        check_transition(BookingStatus.DECLINED, BookingStatus.CONFIRMED)


def test_every_status_has_rules_and_a_label() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(BookingStatus)
    assert set(STATUS_LABELS) == set(BookingStatus)
