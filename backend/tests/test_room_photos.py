from pathlib import Path
from typing import Any

from httpx import AsyncClient

from tests.test_images import make_image

MEDIA_URL = "/api/v1/admin/media"
ROOM_TYPES_URL = "/api/v1/admin/room-types"
PUBLIC_ROOMS_URL = "/api/v1/rooms"


async def upload_photo(client: AsyncClient) -> int:
    response = await client.post(
        MEDIA_URL, files={"file": ("photo.jpg", make_image(1200, 800), "image/jpeg")}
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def room_payload(photos: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "is_active": True,
        "photos": photos,
        "translations": [
            {"locale": "fr", "name": "Bungalow Vue Mer"},
            {"locale": "en", "name": "Sea View Bungalow"},
        ],
    }


async def test_first_photo_becomes_cover_and_order_is_kept(
    owner_client: AsyncClient, media_root: Path
) -> None:
    first, second = await upload_photo(owner_client), await upload_photo(owner_client)

    response = await owner_client.post(
        ROOM_TYPES_URL,
        json=room_payload([{"media_asset_id": second}, {"media_asset_id": first}]),
    )

    assert response.status_code == 201, response.text
    photos = response.json()["photos"]
    assert [(p["media_asset_id"], p["position"], p["is_cover"]) for p in photos] == [
        (second, 0, True),
        (first, 1, False),
    ]


async def test_cover_can_be_moved_to_another_photo(
    owner_client: AsyncClient, media_root: Path
) -> None:
    first, second = await upload_photo(owner_client), await upload_photo(owner_client)
    room = (
        await owner_client.post(
            ROOM_TYPES_URL,
            json=room_payload([{"media_asset_id": first}, {"media_asset_id": second}]),
        )
    ).json()

    response = await owner_client.put(
        f"{ROOM_TYPES_URL}/{room['id']}",
        json=room_payload(
            [{"media_asset_id": first}, {"media_asset_id": second, "is_cover": True}]
        ),
    )

    assert response.status_code == 200, response.text
    covers = [p["media_asset_id"] for p in response.json()["photos"] if p["is_cover"]]
    assert covers == [second]


async def test_two_covers_are_rejected(owner_client: AsyncClient, media_root: Path) -> None:
    first, second = await upload_photo(owner_client), await upload_photo(owner_client)

    response = await owner_client.post(
        ROOM_TYPES_URL,
        json=room_payload(
            [
                {"media_asset_id": first, "is_cover": True},
                {"media_asset_id": second, "is_cover": True},
            ]
        ),
    )

    assert response.status_code == 422


async def test_unknown_photo_is_rejected(owner_client: AsyncClient) -> None:
    response = await owner_client.post(ROOM_TYPES_URL, json=room_payload([{"media_asset_id": 999}]))

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


async def test_public_room_exposes_photos_with_localized_alt_text(
    owner_client: AsyncClient, media_root: Path
) -> None:
    described, undescribed = await upload_photo(owner_client), await upload_photo(owner_client)
    await owner_client.put(
        f"{MEDIA_URL}/{described}/translations",
        json={"translations": [{"locale": "en", "alt_text": "Bungalow facing the lagoon"}]},
    )
    await owner_client.post(
        ROOM_TYPES_URL,
        json=room_payload([{"media_asset_id": described}, {"media_asset_id": undescribed}]),
    )

    room = (
        await owner_client.get(f"{PUBLIC_ROOMS_URL}/sea-view-bungalow", params={"locale": "en"})
    ).json()

    assert [photo["alt"] for photo in room["photos"]] == [
        "Bungalow facing the lagoon",
        "Sea View Bungalow",
    ]
    assert room["photos"][0]["is_cover"] is True
    assert set(room["photos"][0]["variants"]) == {"md"} | {"sm"}


async def test_deleting_a_media_removes_it_from_the_room(
    owner_client: AsyncClient, media_root: Path
) -> None:
    photo = await upload_photo(owner_client)
    room = (
        await owner_client.post(ROOM_TYPES_URL, json=room_payload([{"media_asset_id": photo}]))
    ).json()

    await owner_client.delete(f"{MEDIA_URL}/{photo}")

    refreshed = (await owner_client.get(f"{ROOM_TYPES_URL}/{room['id']}")).json()
    assert refreshed["photos"] == []
