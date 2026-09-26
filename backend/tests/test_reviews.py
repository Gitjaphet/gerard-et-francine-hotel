from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.core.review import ReviewStatus
from app.core.security import hash_ip
from app.db.session import AsyncSessionLocal
from app.models.review import Review
from app.services import review as review_module
from app.services.review import summarize

REVIEWS_URL = "/api/v1/reviews"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_module, "hotel_today", lambda: date(2027, 1, 1))


def review_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "author_name": "Jeanne",
        "author_country": "France",
        "email": "jeanne@example.com",
        "rating": 5,
        "title": "Un petit paradis",
        "body": "Accueil chaleureux, jardin magnifique et plage juste devant.",
        "locale": "fr",
        "stayed_on": "2026-11-15",
        **overrides,
    }


async def approve_all() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(update(Review).values(status=ReviewStatus.APPROVED))
        await db.commit()


# --- Empreinte d'IP et note moyenne (logique pure) -------------------------------


def test_ip_hash_is_stable_distinct_and_does_not_reveal_the_ip() -> None:
    first = hash_ip("203.0.113.7")

    assert first == hash_ip("203.0.113.7")
    assert first != hash_ip("203.0.113.8")
    assert "203.0.113.7" not in first
    assert len(first) == 64


def test_summary_of_no_review_has_no_average() -> None:
    summary = summarize({})

    assert summary.count == 0
    assert summary.average is None
    assert summary.distribution == {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}


def test_average_is_rounded_half_up_to_one_decimal() -> None:
    summary = summarize({1: 1, 2: 1, 3: 2})

    assert summary.count == 4
    assert summary.average == Decimal("2.3")


# --- Dépôt d'un avis --------------------------------------------------------------


async def test_new_review_waits_for_moderation(client: AsyncClient) -> None:
    response = await client.post(REVIEWS_URL, json=review_payload())

    assert response.status_code == 201
    assert response.json() == {"status": "pending"}
    assert (await client.get(REVIEWS_URL)).json()["items"] == []


async def test_a_fourth_review_from_the_same_ip_is_refused(client: AsyncClient) -> None:
    for _ in range(3):
        assert (await client.post(REVIEWS_URL, json=review_payload())).status_code == 201

    response = await client.post(REVIEWS_URL, json=review_payload())

    assert response.status_code == 429


@pytest.mark.parametrize(
    "overrides",
    [
        {"website": "http://spam.example"},
        {"body": "Trop court."},
        {"rating": 6},
        {"rating": 0},
        {"stayed_on": "2027-06-01"},
        {"email": "pas-un-email"},
    ],
    ids=[
        "honeypot",
        "body-too-short",
        "rating-too-high",
        "rating-too-low",
        "future-stay",
        "bad-email",
    ],
)
async def test_invalid_reviews_are_rejected(client: AsyncClient, overrides: dict[str, Any]) -> None:
    response = await client.post(REVIEWS_URL, json=review_payload(**overrides))

    assert response.status_code == 422


# --- Affichage public -------------------------------------------------------------


async def test_public_reviews_never_expose_private_data(client: AsyncClient) -> None:
    await client.post(REVIEWS_URL, json=review_payload())
    await approve_all()

    review = (await client.get(REVIEWS_URL)).json()["items"][0]

    assert review["author_name"] == "Jeanne"
    assert not {"email", "ip_hash", "status", "moderated_by_id"} & review.keys()


async def test_reviews_in_the_visitor_language_come_first(client: AsyncClient) -> None:
    await client.post(REVIEWS_URL, json=review_payload(locale="de", author_name="Hans"))
    await client.post(REVIEWS_URL, json=review_payload(locale="fr", author_name="Jeanne"))
    await approve_all()

    german_page = (await client.get(REVIEWS_URL, params={"locale": "de"})).json()

    assert [r["author_name"] for r in german_page["items"]] == ["Hans", "Jeanne"]


async def test_reviews_are_paginated(client: AsyncClient) -> None:
    for index in range(3):
        await client.post(REVIEWS_URL, json=review_payload(author_name=f"Auteur {index}"))
    await approve_all()

    page = (await client.get(REVIEWS_URL, params={"page": 2, "page_size": 2})).json()

    assert page["total"] == 3
    assert len(page["items"]) == 1


async def test_summary_only_counts_approved_reviews(client: AsyncClient) -> None:
    await client.post(REVIEWS_URL, json=review_payload(rating=5))
    await client.post(REVIEWS_URL, json=review_payload(rating=4))
    await approve_all()
    await client.post(REVIEWS_URL, json=review_payload(rating=1))

    summary = (await client.get(f"{REVIEWS_URL}/summary")).json()

    assert summary["count"] == 2
    assert summary["average"] == "4.5"
    assert summary["distribution"]["1"] == 0
