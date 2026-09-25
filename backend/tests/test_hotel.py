from typing import Any

from httpx import AsyncClient, Response

SETTINGS_URL = "/api/v1/admin/hotel-settings"
SOCIAL_URL = "/api/v1/admin/social-links"
PUBLIC_URL = "/api/v1/hotel"

VALID_SETTINGS: dict[str, Any] = {
    "name": "Gérard et Francine",
    "email": "contact@example.com",
    "stars": 3,
    "whatsapp": "+261320000000",
    "nif": "NIF-123",
    "stat": "STAT-456",
    "google_place_id": "place-789",
    "translations": [
        {"locale": "fr", "tagline": "Hôtel de charme"},
        {"locale": "en", "tagline": "Charming hotel"},
    ],
}


async def put_settings(client: AsyncClient, **overrides: Any) -> Response:
    return await client.put(SETTINGS_URL, json={**VALID_SETTINGS, **overrides})


# --- Réglages (admin) --------------------------------------------------------


async def test_settings_are_not_found_before_first_save(owner_client: AsyncClient) -> None:
    response = await owner_client.get(SETTINGS_URL)

    assert response.status_code == 404


async def test_first_save_creates_settings_with_translations(owner_client: AsyncClient) -> None:
    response = await put_settings(owner_client)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gérard et Francine"
    assert body["country"] == "Madagascar"
    assert {t["locale"] for t in body["translations"]} == {"fr", "en"}


async def test_update_keeps_the_same_row_and_preserves_missing_translations(
    owner_client: AsyncClient,
) -> None:
    first = (await put_settings(owner_client)).json()

    second = (
        await put_settings(
            owner_client,
            translations=[
                {"locale": "fr", "tagline": "Nouveau slogan"},
                {"locale": "it", "tagline": "Hotel di charme"},
            ],
        )
    ).json()

    assert second["id"] == first["id"]
    taglines = {t["locale"]: t["tagline"] for t in second["translations"]}
    assert taglines == {"fr": "Nouveau slogan", "en": "Charming hotel", "it": "Hotel di charme"}


async def test_duplicate_locales_are_rejected(owner_client: AsyncClient) -> None:
    response = await put_settings(owner_client, translations=[{"locale": "fr"}, {"locale": "fr"}])

    assert response.status_code == 422


async def test_mga_prices_require_an_exchange_rate(owner_client: AsyncClient) -> None:
    response = await put_settings(owner_client, show_mga_prices=True, eur_to_mga_rate=None)

    assert response.status_code == 422


# --- Réseaux sociaux (admin) -------------------------------------------------


async def test_social_link_rejects_non_https_urls(owner_client: AsyncClient) -> None:
    response = await owner_client.post(
        SOCIAL_URL, json={"platform": "facebook", "url": "javascript:alert(1)"}
    )

    assert response.status_code == 422


async def test_deleted_social_link_is_not_found_anymore(owner_client: AsyncClient) -> None:
    link = (
        await owner_client.post(
            SOCIAL_URL, json={"platform": "facebook", "url": "https://facebook.com/gf"}
        )
    ).json()

    assert (await owner_client.delete(f"{SOCIAL_URL}/{link['id']}")).status_code == 204
    assert (await owner_client.delete(f"{SOCIAL_URL}/{link['id']}")).status_code == 404


# --- Vue publique ------------------------------------------------------------


async def test_public_view_returns_requested_locale(owner_client: AsyncClient) -> None:
    await put_settings(owner_client)

    body = (await owner_client.get(PUBLIC_URL, params={"locale": "en"})).json()

    assert body["tagline"] == "Charming hotel"
    assert body["content_locale"] == "en"
    assert body["available_locales"] == ["fr", "en"]


async def test_public_view_falls_back_to_french(owner_client: AsyncClient) -> None:
    await put_settings(owner_client)

    body = (await owner_client.get(PUBLIC_URL, params={"locale": "de"})).json()

    assert body["locale"] == "de"
    assert body["content_locale"] == "fr"
    assert body["tagline"] == "Hôtel de charme"


async def test_public_view_hides_private_fields_and_inactive_links(
    owner_client: AsyncClient,
) -> None:
    await put_settings(owner_client)
    await owner_client.post(
        SOCIAL_URL, json={"platform": "instagram", "url": "https://instagram.com/gf"}
    )
    await owner_client.post(
        SOCIAL_URL,
        json={"platform": "facebook", "url": "https://facebook.com/gf", "is_active": False},
    )

    body = (await owner_client.get(PUBLIC_URL)).json()

    assert not {"nif", "stat", "google_place_id", "eur_to_mga_rate"} & body.keys()
    assert [link["platform"] for link in body["social_links"]] == ["instagram"]


async def test_public_view_is_accessible_without_login(client: AsyncClient) -> None:
    response = await client.get(PUBLIC_URL)

    assert response.status_code == 404


async def test_public_view_rejects_unsupported_locales(client: AsyncClient) -> None:
    response = await client.get(PUBLIC_URL, params={"locale": "es"})

    assert response.status_code == 422
