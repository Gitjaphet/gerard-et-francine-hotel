from datetime import date

import pytest
from httpx import AsyncClient

from app.core.roles import UserRole
from app.services import review as review_module
from tests.conftest import TEST_PASSWORD, UserFactory
from tests.test_reviews import REVIEWS_URL, review_payload

ADMIN_URL = "/api/v1/admin/reviews"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_module, "hotel_today", lambda: date(2027, 1, 1))


async def submit_review(client: AsyncClient, **overrides: object) -> int:
    await client.post(REVIEWS_URL, json=review_payload(**overrides))
    reviews = (await client.get(ADMIN_URL, params={"status": "pending"})).json()
    return int(reviews[0]["id"])


async def test_staff_can_approve_a_review_which_becomes_public(
    owner_client: AsyncClient, make_user: UserFactory
) -> None:
    staff = await make_user(email="staff@example.com", role=UserRole.STAFF)
    await owner_client.post(
        "/api/v1/auth/login", json={"email": staff.email, "password": TEST_PASSWORD}
    )
    review_id = await submit_review(owner_client)

    response = await owner_client.post(
        f"{ADMIN_URL}/{review_id}/moderation", json={"status": "approved"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["moderated_by_id"] == staff.id
    assert response.json()["moderated_at"] is not None
    assert len((await owner_client.get(REVIEWS_URL)).json()["items"]) == 1


async def test_published_review_can_be_withdrawn(owner_client: AsyncClient) -> None:
    review_id = await submit_review(owner_client)
    await owner_client.post(f"{ADMIN_URL}/{review_id}/moderation", json={"status": "approved"})

    await owner_client.post(f"{ADMIN_URL}/{review_id}/moderation", json={"status": "rejected"})

    assert (await owner_client.get(REVIEWS_URL)).json()["items"] == []


async def test_a_review_cannot_go_back_to_pending(owner_client: AsyncClient) -> None:
    review_id = await submit_review(owner_client)

    response = await owner_client.post(
        f"{ADMIN_URL}/{review_id}/moderation", json={"status": "pending"}
    )

    assert response.status_code == 422


async def test_owner_reply_is_published_with_the_review(owner_client: AsyncClient) -> None:
    review_id = await submit_review(owner_client)
    await owner_client.post(f"{ADMIN_URL}/{review_id}/moderation", json={"status": "approved"})

    await owner_client.put(
        f"{ADMIN_URL}/{review_id}/reply", json={"owner_reply": "  Merci Jeanne, à bientôt !  "}
    )

    review = (await owner_client.get(REVIEWS_URL)).json()["items"][0]
    assert review["owner_reply"] == "Merci Jeanne, à bientôt !"


async def test_empty_reply_removes_the_reply(owner_client: AsyncClient) -> None:
    review_id = await submit_review(owner_client)
    await owner_client.put(f"{ADMIN_URL}/{review_id}/reply", json={"owner_reply": "Merci"})

    response = await owner_client.put(f"{ADMIN_URL}/{review_id}/reply", json={"owner_reply": "  "})

    assert response.json()["owner_reply"] is None


async def test_admin_sees_private_data_that_the_public_never_sees(
    owner_client: AsyncClient,
) -> None:
    review_id = await submit_review(owner_client)

    review = (await owner_client.get(f"{ADMIN_URL}/{review_id}")).json()

    assert review["email"] == "jeanne@example.com"
    assert "ip_hash" not in review


async def test_spam_can_be_deleted(owner_client: AsyncClient) -> None:
    review_id = await submit_review(owner_client)

    assert (await owner_client.delete(f"{ADMIN_URL}/{review_id}")).status_code == 204
    assert (await owner_client.get(f"{ADMIN_URL}/{review_id}")).status_code == 404


async def test_moderation_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get(ADMIN_URL)).status_code == 401
