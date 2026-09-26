from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.booking import BookingRequest
from app.services import booking as booking_module
from tests.test_rooms import create_room

BOOKING_URL = "/api/v1/booking-requests"
SEASONS_URL = "/api/v1/admin/seasons"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking_module, "hotel_today", lambda: date(2027, 1, 1))


def request_payload(room_type_id: int, **overrides: Any) -> dict[str, Any]:
    return {
        "room_type_id": room_type_id,
        "check_in": "2027-03-10",
        "check_out": "2027-03-13",
        "adults": 2,
        "guest_name": "  Jeanne Martin ",
        "email": "Jeanne.Martin@Example.com",
        "phone": "+33 6 12 34 56 78",
        "prefers_whatsapp": True,
        "locale": "fr",
        **overrides,
    }


async def test_valid_request_is_stored_as_pending_with_its_price(
    owner_client: AsyncClient,
) -> None:
    room = await create_room(owner_client, base_price="45.00")

    response = await owner_client.post(BOOKING_URL, json=request_payload(room["id"]))

    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["reference"].startswith("GF-")
    assert receipt["status"] == "pending"
    assert receipt["quoted_total"] == "135.00"
    assert receipt["warnings"] == []
    assert "staff_notes" not in receipt

    async with AsyncSessionLocal() as db:
        stored = (await db.execute(select(BookingRequest))).scalar_one()
    assert stored.guest_name == "Jeanne Martin"
    assert stored.email == "jeanne.martin@example.com"
    assert stored.room_name == "Bungalow Vue Mer"


async def test_over_capacity_request_is_accepted_with_a_warning(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")

    response = await owner_client.post(BOOKING_URL, json=request_payload(room["id"], adults=4))

    assert response.status_code == 201
    assert response.json()["warnings"] == ["over_capacity"]


async def test_short_stay_is_accepted_with_its_price_and_minimum(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    await owner_client.post(
        SEASONS_URL,
        json={
            "start_date": "2027-12-20",
            "end_date": "2028-01-05",
            "min_nights": 5,
            "translations": [{"locale": "fr", "name": "Fêtes"}],
        },
    )

    response = await owner_client.post(
        BOOKING_URL,
        json=request_payload(room["id"], check_in="2027-12-22", check_out="2027-12-24"),
    )

    receipt = response.json()
    assert response.status_code == 201
    assert receipt["warnings"] == ["min_stay_not_met"]
    assert receipt["quoted_total"] == "90.00"
    assert receipt["min_nights_required"] == 5


async def test_request_without_price_is_accepted_with_a_warning(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client)

    response = await owner_client.post(BOOKING_URL, json=request_payload(room["id"]))

    assert response.status_code == 201
    assert response.json()["quoted_total"] is None
    assert response.json()["warnings"] == ["price_unavailable"]


async def test_booking_form_is_public(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    await owner_client.post("/api/v1/auth/logout")

    response = await owner_client.post(BOOKING_URL, json=request_payload(room["id"]))

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("overrides", "expected_status"),
    [
        ({"website": "http://spam.example"}, 422),
        ({"check_in": "2026-12-20", "check_out": "2026-12-23"}, 422),
        ({"check_out": "2027-03-10"}, 422),
        ({"prefers_whatsapp": True, "phone": None}, 422),
        ({"children": 2, "children_ages": [4]}, 422),
        ({"email": "pas-un-email"}, 422),
        ({"adults": 0}, 422),
    ],
    ids=[
        "honeypot-filled",
        "arrival-in-the-past",
        "departure-not-after-arrival",
        "whatsapp-without-phone",
        "missing-child-age",
        "invalid-email",
        "no-adult",
    ],
)
async def test_impossible_requests_are_rejected(
    owner_client: AsyncClient, overrides: dict[str, Any], expected_status: int
) -> None:
    room = await create_room(owner_client, base_price="45.00")

    response = await owner_client.post(BOOKING_URL, json=request_payload(room["id"], **overrides))

    assert response.status_code == expected_status, response.text


async def test_unpublished_room_cannot_be_requested(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00", is_active=False)

    response = await owner_client.post(BOOKING_URL, json=request_payload(room["id"]))

    assert response.status_code == 404
