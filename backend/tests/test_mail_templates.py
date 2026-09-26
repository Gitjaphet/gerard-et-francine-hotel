from datetime import date
from decimal import Decimal

import pytest

from app.core.i18n import Locale
from app.mail.templates import format_price, guest_acknowledgement, reception_alert
from app.models.booking import BookingRequest


def make_booking(**overrides: object) -> BookingRequest:
    values: dict[str, object] = {
        "id": 42,
        "reference": "GF-00042",
        "room_name": "Bungalow Vue Mer",
        "check_in": date(2027, 3, 10),
        "check_out": date(2027, 3, 13),
        "adults": 2,
        "children": 1,
        "children_ages": [6],
        "nights_count": 3,
        "quoted_total": Decimal("1135.00"),
        "warnings": [],
        "guest_name": "Jeanne Martin",
        "email": "jeanne@example.com",
        "phone": "+33 6 12 34 56 78",
        "prefers_whatsapp": True,
        "locale": Locale.FR,
        "message": "Arrivée tardive vers 22 h.",
    }
    values.update(overrides)
    return BookingRequest(**values)


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        (Locale.FR, "1\u202f135,00 €"),
        (Locale.IT, "1\u202f135,00 €"),
        (Locale.DE, "1\u202f135,00 €"),
        (Locale.EN, "€1,135.00"),
    ],
)
def test_prices_follow_each_country_format(locale: Locale, expected: str) -> None:
    assert format_price(Decimal("1135.00"), locale) == expected


@pytest.mark.parametrize(
    ("locale", "subject_start"),
    [
        (Locale.FR, "Votre demande de réservation GF-00042"),
        (Locale.EN, "Your booking request GF-00042"),
        (Locale.IT, "La sua richiesta di prenotazione GF-00042"),
        (Locale.DE, "Ihre Buchungsanfrage GF-00042"),
    ],
)
def test_guest_email_is_written_in_the_guest_language(locale: Locale, subject_start: str) -> None:
    email = guest_acknowledgement(make_booking(locale=locale), min_nights_required=None)

    assert email.to == "jeanne@example.com"
    assert email.subject.startswith(subject_start)
    assert "Jeanne Martin" in email.body
    assert "10/03/2027" in email.body


def test_guest_email_explains_warnings_honestly() -> None:
    booking = make_booking(warnings=["over_capacity", "min_stay_not_met"])

    body = guest_acknowledgement(booking, min_nights_required=5).body

    assert "seconde chambre ou lit supplémentaire" in body
    assert "séjour minimum sur ces dates est de 5 nuits" in body


def test_guest_email_without_price_announces_it_later() -> None:
    booking = make_booking(quoted_total=None, warnings=["price_unavailable"])

    body = guest_acknowledgement(booking, min_nights_required=None).body

    assert "Le prix vous sera communiqué par notre réception." in body


def test_reception_alert_has_everything_to_handle_the_request() -> None:
    booking = make_booking(warnings=["over_capacity"])

    email = reception_alert(
        booking, reception_email="reception@example.com", admin_base_url="https://gf.test/admin/"
    )

    assert email.to == "reception@example.com"
    assert email.reply_to == "jeanne@example.com"
    assert "GF-00042" in email.subject
    assert "Capacité dépassée" in email.body
    assert "(préfère WhatsApp)" in email.body
    assert "âges : 6" in email.body
    assert "https://gf.test/admin/booking-requests/42" in email.body
