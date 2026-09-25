from typing import Any

import pytest
from httpx import AsyncClient

from app.services.season import SeasonService
from tests.test_rooms import create_room

SEASONS_URL = "/api/v1/admin/seasons"


def season_payload(
    start: str, end: str, name: str = "Haute saison", **extra: Any
) -> dict[str, Any]:
    return {
        "start_date": start,
        "end_date": end,
        "translations": [{"locale": "fr", "name": name}],
        **extra,
    }


async def test_season_is_created_with_its_rates(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client)

    response = await owner_client.post(
        SEASONS_URL,
        json=season_payload(
            "2026-07-01", "2026-10-31", rates=[{"room_type_id": room["id"], "price": "65.00"}]
        ),
    )

    assert response.status_code == 201, response.text
    assert response.json()["rates"] == [{"room_type_id": room["id"], "price": "65.00"}]


async def test_overlapping_season_is_rejected_with_a_helpful_message(
    owner_client: AsyncClient,
) -> None:
    await owner_client.post(SEASONS_URL, json=season_payload("2026-07-01", "2026-10-31"))

    response = await owner_client.post(
        SEASONS_URL, json=season_payload("2026-10-31", "2026-12-15", name="Fêtes")
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "Haute saison" in detail
    assert "du 01/07/2026 au 31/10/2026" in detail


async def test_adjacent_seasons_are_allowed(owner_client: AsyncClient) -> None:
    await owner_client.post(SEASONS_URL, json=season_payload("2026-07-01", "2026-10-31"))

    response = await owner_client.post(
        SEASONS_URL, json=season_payload("2026-11-01", "2026-12-15", name="Basse saison")
    )

    assert response.status_code == 201


async def test_database_constraint_catches_overlaps_the_precheck_missed(
    owner_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await owner_client.post(SEASONS_URL, json=season_payload("2026-07-01", "2026-10-31"))

    async def skip_precheck(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(SeasonService, "_ensure_no_overlap", skip_precheck)
    response = await owner_client.post(SEASONS_URL, json=season_payload("2026-08-01", "2026-08-31"))

    assert response.status_code == 409
    assert response.json()["detail"] == "Cette période chevauche une autre saison."


async def test_season_can_be_updated_without_overlapping_itself(owner_client: AsyncClient) -> None:
    season = (
        await owner_client.post(SEASONS_URL, json=season_payload("2026-07-01", "2026-10-31"))
    ).json()

    response = await owner_client.put(
        f"{SEASONS_URL}/{season['id']}",
        json=season_payload("2026-07-01", "2026-11-15", min_nights=3),
    )

    assert response.status_code == 200, response.text
    assert response.json()["end_date"] == "2026-11-15"
    assert response.json()["min_nights"] == 3


async def test_rates_are_replaced_on_update(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client)
    season = (
        await owner_client.post(
            SEASONS_URL,
            json=season_payload(
                "2026-07-01", "2026-10-31", rates=[{"room_type_id": room["id"], "price": "65.00"}]
            ),
        )
    ).json()

    response = await owner_client.put(
        f"{SEASONS_URL}/{season['id']}", json=season_payload("2026-07-01", "2026-10-31", rates=[])
    )

    assert response.json()["rates"] == []


@pytest.mark.parametrize(
    "payload",
    [
        season_payload("2026-10-31", "2026-07-01"),
        season_payload("2026-07-01", "2026-10-31", rates=[{"room_type_id": 1, "price": "0"}]),
        season_payload("2026-07-01", "2026-10-31", rates=[{"room_type_id": 1, "price": "45.999"}]),
        {
            "start_date": "2026-07-01",
            "end_date": "2026-10-31",
            "translations": [{"locale": "en", "name": "High"}],
        },
    ],
    ids=["end-before-start", "zero-price", "three-decimals", "missing-french"],
)
async def test_invalid_seasons_are_rejected(
    owner_client: AsyncClient, payload: dict[str, Any]
) -> None:
    response = await owner_client.post(SEASONS_URL, json=payload)

    assert response.status_code == 422


async def test_rate_for_unknown_room_type_is_rejected(owner_client: AsyncClient) -> None:
    response = await owner_client.post(
        SEASONS_URL,
        json=season_payload(
            "2026-07-01", "2026-10-31", rates=[{"room_type_id": 999, "price": "65.00"}]
        ),
    )

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


async def test_seasons_admin_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get(SEASONS_URL)).status_code == 401
