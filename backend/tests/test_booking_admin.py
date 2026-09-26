from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.roles import UserRole
from app.services import booking as booking_module
from tests.conftest import TEST_PASSWORD, UserFactory
from tests.test_rooms import create_room

BOOKING_URL = "/api/v1/booking-requests"
ADMIN_URL = "/api/v1/admin/booking-requests"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(booking_module, "hotel_today", lambda: date(2027, 1, 1))


async def request_booking(
    client: AsyncClient, room_type_id: int, check_in: str, check_out: str, **extra: Any
) -> int:
    response = await client.post(
        BOOKING_URL,
        json={
            "room_type_id": room_type_id,
            "check_in": check_in,
            "check_out": check_out,
            "adults": 2,
            "guest_name": "Jeanne Martin",
            "email": "jeanne@example.com",
            "phone": "+33 6 12 34 56 78",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    bookings = (await client.get(ADMIN_URL)).json()
    return int(next(b["id"] for b in bookings if b["reference"] == response.json()["reference"]))


async def login_as_staff(client: AsyncClient, make_user: UserFactory) -> int:
    staff = await make_user(email="staff@example.com", role=UserRole.STAFF)
    response = await client.post(
        "/api/v1/auth/login", json={"email": staff.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    return staff.id


async def test_staff_can_manage_bookings_but_not_hotel_settings(
    owner_client: AsyncClient, make_user: UserFactory
) -> None:
    room = await create_room(owner_client, base_price="45.00")
    booking_id = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")

    await login_as_staff(owner_client, make_user)

    assert (await owner_client.get(ADMIN_URL)).status_code == 200
    assert (await owner_client.get(f"{ADMIN_URL}/{booking_id}")).status_code == 200
    assert (await owner_client.get("/api/v1/admin/hotel-settings")).status_code == 403


async def test_anonymous_users_cannot_see_bookings(client: AsyncClient) -> None:
    assert (await client.get(ADMIN_URL)).status_code == 401


async def test_confirming_records_who_and_when(
    owner_client: AsyncClient, make_user: UserFactory
) -> None:
    room = await create_room(owner_client, base_price="45.00")
    booking_id = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")
    staff_id = await login_as_staff(owner_client, make_user)

    response = await owner_client.post(
        f"{ADMIN_URL}/{booking_id}/status", json={"status": "confirmed"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["handled_by_id"] == staff_id
    assert body["status_changed_at"] is not None


async def test_forbidden_transition_returns_409(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    booking_id = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")
    await owner_client.post(f"{ADMIN_URL}/{booking_id}/status", json={"status": "declined"})

    response = await owner_client.post(
        f"{ADMIN_URL}/{booking_id}/status", json={"status": "confirmed"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Une demande refusée ne peut pas être confirmée."


async def test_detail_counts_confirmed_overlapping_requests(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    confirmed = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")
    await owner_client.post(f"{ADMIN_URL}/{confirmed}/status", json={"status": "confirmed"})
    overlapping = await request_booking(owner_client, room["id"], "2027-03-12", "2027-03-15")
    adjacent = await request_booking(owner_client, room["id"], "2027-03-13", "2027-03-16")
    pending_only = await request_booking(owner_client, room["id"], "2027-04-01", "2027-04-03")

    counts = {
        booking_id: (await owner_client.get(f"{ADMIN_URL}/{booking_id}")).json()[
            "overlapping_confirmed"
        ]
        for booking_id in (overlapping, adjacent, pending_only)
    }

    assert counts == {overlapping: 1, adjacent: 0, pending_only: 0}


async def test_detail_offers_a_whatsapp_link(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    booking_id = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")

    detail = (await owner_client.get(f"{ADMIN_URL}/{booking_id}")).json()

    assert detail["whatsapp_url"] == "https://wa.me/33612345678"


async def test_staff_notes_are_saved(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    booking_id = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")

    response = await owner_client.put(
        f"{ADMIN_URL}/{booking_id}/notes",
        json={"staff_notes": "Client rappelé, propose le bungalow voisin."},
    )

    assert response.status_code == 200
    assert response.json()["staff_notes"] == "Client rappelé, propose le bungalow voisin."


async def test_list_can_be_filtered_by_status(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    first = await request_booking(owner_client, room["id"], "2027-03-10", "2027-03-13")
    await request_booking(owner_client, room["id"], "2027-04-10", "2027-04-13")
    await owner_client.post(f"{ADMIN_URL}/{first}/status", json={"status": "confirmed"})

    confirmed = (await owner_client.get(ADMIN_URL, params={"status": "confirmed"})).json()
    pending = (await owner_client.get(ADMIN_URL, params={"status": "pending"})).json()

    assert [b["id"] for b in confirmed] == [first]
    assert len(pending) == 1


async def test_unknown_booking_returns_404(owner_client: AsyncClient) -> None:
    assert (await owner_client.get(f"{ADMIN_URL}/999")).status_code == 404
