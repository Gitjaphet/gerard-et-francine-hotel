from typing import Any

from httpx import AsyncClient

AMENITIES_URL = "/api/v1/admin/amenities"
ROOM_TYPES_URL = "/api/v1/admin/room-types"
PUBLIC_ROOMS_URL = "/api/v1/rooms"


async def create_amenity(
    client: AsyncClient, code: str, fr: str, en: str | None = None, position: int = 0
) -> int:
    translations = [{"locale": "fr", "name": fr}]
    if en:
        translations.append({"locale": "en", "name": en})
    response = await client.post(
        AMENITIES_URL,
        json={
            "code": code,
            "icon": code.replace("_", "-"),
            "translations": translations,
            "position": position,
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def create_room(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "max_adults": 2,
        "units_count": 3,
        "is_active": True,
        "translations": [
            {"locale": "fr", "name": "Bungalow Vue Mer"},
            {"locale": "en", "name": "Sea View Bungalow"},
        ],
        **overrides,
    }
    response = await client.post(ROOM_TYPES_URL, json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


# --- Équipements -------------------------------------------------------------


async def test_amenity_code_must_be_unique(owner_client: AsyncClient) -> None:
    await create_amenity(owner_client, "fan", "Ventilateur")

    response = await owner_client.post(
        AMENITIES_URL,
        json={"code": "fan", "icon": "fan", "translations": [{"locale": "fr", "name": "Autre"}]},
    )

    assert response.status_code == 409


# --- Types de chambres (admin) -----------------------------------------------


async def test_room_type_gets_generated_slugs_and_catalog_ordered_amenities(
    owner_client: AsyncClient,
) -> None:
    fan = await create_amenity(owner_client, "fan", "Ventilateur", position=2)
    safe = await create_amenity(owner_client, "safe", "Coffre-fort", position=1)

    room = await create_room(owner_client, amenity_ids=[fan, safe])

    slugs = {t["locale"]: t["slug"] for t in room["translations"]}
    assert slugs == {"fr": "bungalow-vue-mer", "en": "sea-view-bungalow"}
    assert [a["code"] for a in room["amenities"]] == ["safe", "fan"]


async def test_slug_conflict_returns_409(owner_client: AsyncClient) -> None:
    await create_room(owner_client)

    response = await owner_client.post(
        ROOM_TYPES_URL, json={"translations": [{"locale": "fr", "name": "Bungalow vue mer"}]}
    )

    assert response.status_code == 409
    assert "bungalow-vue-mer" in response.json()["detail"]


async def test_update_can_keep_its_own_slug(owner_client: AsyncClient) -> None:
    room = await create_room(owner_client)

    response = await owner_client.put(
        f"{ROOM_TYPES_URL}/{room['id']}",
        json={"units_count": 4, "translations": [{"locale": "fr", "name": "Bungalow Vue Mer"}]},
    )

    assert response.status_code == 200
    assert response.json()["units_count"] == 4


async def test_unknown_amenity_is_rejected(owner_client: AsyncClient) -> None:
    response = await owner_client.post(
        ROOM_TYPES_URL,
        json={"amenity_ids": [999], "translations": [{"locale": "fr", "name": "Suite"}]},
    )

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


async def test_deleting_an_amenity_removes_it_from_rooms(owner_client: AsyncClient) -> None:
    fan = await create_amenity(owner_client, "fan", "Ventilateur")
    room = await create_room(owner_client, amenity_ids=[fan])

    await owner_client.delete(f"{AMENITIES_URL}/{fan}")

    refreshed = (await owner_client.get(f"{ROOM_TYPES_URL}/{room['id']}")).json()
    assert refreshed["amenities"] == []


async def test_room_admin_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get(ROOM_TYPES_URL)).status_code == 401
    assert (await client.get(AMENITIES_URL)).status_code == 401


# --- Vue publique ------------------------------------------------------------


async def test_public_list_only_shows_active_rooms(owner_client: AsyncClient) -> None:
    await create_room(owner_client)
    await create_room(
        owner_client,
        is_active=False,
        translations=[{"locale": "fr", "name": "Nouvelle suite en travaux"}],
    )

    rooms = (await owner_client.get(PUBLIC_ROOMS_URL)).json()

    assert [room["slug"] for room in rooms] == ["bungalow-vue-mer"]
    assert "units_count" not in rooms[0]


async def test_public_room_is_translated_with_amenity_fallback(owner_client: AsyncClient) -> None:
    fan = await create_amenity(owner_client, "fan", "Ventilateur", en="Fan")
    safe = await create_amenity(owner_client, "safe", "Coffre-fort")
    await create_room(owner_client, amenity_ids=[fan, safe])

    response = await owner_client.get(
        f"{PUBLIC_ROOMS_URL}/sea-view-bungalow", params={"locale": "en"}
    )

    assert response.status_code == 200
    room = response.json()
    assert room["name"] == "Sea View Bungalow"
    assert room["slugs"] == {"fr": "bungalow-vue-mer", "en": "sea-view-bungalow"}
    assert [a["name"] for a in room["amenities"]] == ["Fan", "Coffre-fort"]


async def test_slug_is_looked_up_in_the_requested_language(owner_client: AsyncClient) -> None:
    await create_room(owner_client)

    response = await owner_client.get(
        f"{PUBLIC_ROOMS_URL}/bungalow-vue-mer", params={"locale": "en"}
    )

    assert response.status_code == 404


async def test_inactive_room_is_not_reachable_by_slug(owner_client: AsyncClient) -> None:
    await create_room(owner_client, is_active=False)

    response = await owner_client.get(f"{PUBLIC_ROOMS_URL}/bungalow-vue-mer")

    assert response.status_code == 404
