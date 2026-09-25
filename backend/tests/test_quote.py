from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from app.services import quote as quote_module
from tests.test_rooms import create_room

SEASONS_URL = "/api/v1/admin/seasons"
QUOTE_URL = "/api/v1/rooms/bungalow-vue-mer/quote"

# Capturée au chargement, avant que la fixture autouse ne la remplace.
REAL_HOTEL_TODAY = quote_module.hotel_today


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quote_module, "hotel_today", lambda: date(2027, 1, 1))


async def get_quote(client: AsyncClient, check_in: str, check_out: str) -> Any:
    return await client.get(QUOTE_URL, params={"check_in": check_in, "check_out": check_out})


async def test_quote_uses_base_price_outside_seasons(owner_client: AsyncClient) -> None:
    await create_room(owner_client, base_price="45.00")

    response = await get_quote(owner_client, "2027-03-10", "2027-03-13")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["nights_count"] == 3
    assert body["total"] == "135.00"
    assert body["currency"] == "EUR"


async def test_quote_details_each_night_across_a_season_boundary(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client, base_price="45.00")
    await owner_client.post(
        SEASONS_URL,
        json={
            "start_date": "2027-07-01",
            "end_date": "2027-10-31",
            "rates": [{"room_type_id": room["id"], "price": "65.00"}],
            "translations": [{"locale": "fr", "name": "Haute saison"}],
        },
    )

    body = (await get_quote(owner_client, "2027-06-29", "2027-07-02")).json()

    assert [(n["night"], n["price"]) for n in body["nights"]] == [
        ("2027-06-29", "45.00"),
        ("2027-06-30", "45.00"),
        ("2027-07-01", "65.00"),
    ]
    assert body["total"] == "155.00"


async def test_minimum_stay_is_enforced(owner_client: AsyncClient) -> None:
    await create_room(owner_client, base_price="45.00")
    await owner_client.post(
        SEASONS_URL,
        json={
            "start_date": "2027-12-20",
            "end_date": "2028-01-05",
            "min_nights": 5,
            "translations": [{"locale": "fr", "name": "Fêtes"}],
        },
    )

    response = await get_quote(owner_client, "2027-12-22", "2027-12-24")

    assert response.status_code == 422
    assert "minimum de 5 nuits" in response.json()["detail"]


async def test_missing_price_is_reported(owner_client: AsyncClient) -> None:
    await create_room(owner_client)

    response = await get_quote(owner_client, "2027-03-10", "2027-03-12")

    assert response.status_code == 422
    assert "10/03/2027" in response.json()["detail"]


@pytest.mark.parametrize(
    ("check_in", "check_out", "message"),
    [
        ("2026-12-31", "2027-01-03", "passé"),
        ("2027-03-10", "2027-03-10", "postérieure"),
        ("2027-03-10", "2027-03-08", "postérieure"),
    ],
    ids=["arrival-in-the-past", "same-day", "departure-before-arrival"],
)
async def test_invalid_dates_are_rejected(
    owner_client: AsyncClient, check_in: str, check_out: str, message: str
) -> None:
    await create_room(owner_client, base_price="45.00")

    response = await get_quote(owner_client, check_in, check_out)

    assert response.status_code == 422
    assert message in response.json()["detail"]


async def test_quote_is_not_available_for_unpublished_rooms(owner_client: AsyncClient) -> None:
    await create_room(owner_client, base_price="45.00", is_active=False)

    response = await get_quote(owner_client, "2027-03-10", "2027-03-13")

    assert response.status_code == 404


async def test_quote_is_public(client: AsyncClient) -> None:
    response = await client.get(
        QUOTE_URL, params={"check_in": "2027-03-10", "check_out": "2027-03-13"}
    )

    assert response.status_code == 404


def test_hotel_today_uses_the_hotel_timezone() -> None:
    today = REAL_HOTEL_TODAY()

    assert isinstance(today, date)
    assert abs(today - date.today()) <= timedelta(days=1)
