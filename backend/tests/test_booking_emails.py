import logging
from collections.abc import Iterator
from datetime import date

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.mail.base import OutgoingEmail
from app.mail.deps import get_mailer
from app.main import app
from app.services import booking as booking_module
from tests.test_rooms import create_room

BOOKING_URL = "/api/v1/booking-requests"


class RecordingMailer:
    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[OutgoingEmail] = []
        self.fail = fail

    async def send(self, email: OutgoingEmail) -> None:
        if self.fail:
            raise ConnectionError("SMTP injoignable")
        self.sent.append(email)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking_module, "hotel_today", lambda: date(2027, 1, 1))
    monkeypatch.setattr(get_settings(), "reception_email", "reception@example.com")


@pytest.fixture
def mailer() -> Iterator[RecordingMailer]:
    recording = RecordingMailer()
    app.dependency_overrides[get_mailer] = lambda: recording
    yield recording
    app.dependency_overrides.pop(get_mailer, None)


def booking_payload(room_type_id: int) -> dict[str, object]:
    return {
        "room_type_id": room_type_id,
        "check_in": "2027-03-10",
        "check_out": "2027-03-13",
        "adults": 2,
        "guest_name": "Hans Weber",
        "email": "hans@example.de",
        "locale": "de",
    }


async def test_guest_and_reception_are_notified(
    owner_client: AsyncClient, mailer: RecordingMailer
) -> None:
    room = await create_room(owner_client, base_price="45.00")

    response = await owner_client.post(BOOKING_URL, json=booking_payload(room["id"]))

    assert response.status_code == 201
    guest, reception = mailer.sent
    assert guest.to == "hans@example.de"
    assert guest.subject.startswith("Ihre Buchungsanfrage GF-")
    assert reception.to == "reception@example.com"
    assert reception.reply_to == "hans@example.de"


async def test_booking_is_saved_even_when_email_fails(
    owner_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    room = await create_room(owner_client, base_price="45.00")
    app.dependency_overrides[get_mailer] = lambda: RecordingMailer(fail=True)
    try:
        with caplog.at_level(logging.ERROR):
            response = await owner_client.post(BOOKING_URL, json=booking_payload(room["id"]))
    finally:
        app.dependency_overrides.pop(get_mailer, None)

    assert response.status_code == 201
    assert "Échec de l'envoi" in caplog.text
    bookings = (await owner_client.get("/api/v1/admin/booking-requests")).json()
    assert len(bookings) == 1
