from httpx import AsyncClient

from app.core.roles import UserRole
from tests.conftest import TEST_PASSWORD, UserFactory

LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
ADMIN_URL = "/api/v1/admin/hotel-settings"


async def test_login_sets_secure_session_cookie(
    client: AsyncClient, make_user: UserFactory
) -> None:
    await make_user()

    response = await client.post(
        LOGIN_URL, json={"email": "owner@example.com", "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    assert "hashed_password" not in response.json()
    cookie = response.headers["set-cookie"]
    assert "gf_admin_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


async def test_login_normalizes_email_case(client: AsyncClient, make_user: UserFactory) -> None:
    await make_user()

    response = await client.post(
        LOGIN_URL, json={"email": "  Owner@Example.COM ", "password": TEST_PASSWORD}
    )

    assert response.status_code == 200


async def test_wrong_password_and_unknown_email_return_same_error(
    client: AsyncClient, make_user: UserFactory
) -> None:
    await make_user()

    wrong_password = await client.post(
        LOGIN_URL, json={"email": "owner@example.com", "password": "not-the-password"}
    )
    unknown_email = await client.post(
        LOGIN_URL, json={"email": "nobody@example.com", "password": TEST_PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_inactive_user_cannot_login(client: AsyncClient, make_user: UserFactory) -> None:
    await make_user(is_active=False)

    response = await client.post(
        LOGIN_URL, json={"email": "owner@example.com", "password": TEST_PASSWORD}
    )

    assert response.status_code == 401


async def test_account_is_locked_after_five_failures(
    client: AsyncClient, make_user: UserFactory
) -> None:
    await make_user()
    bad_credentials = {"email": "owner@example.com", "password": "not-the-password"}

    for _ in range(5):
        assert (await client.post(LOGIN_URL, json=bad_credentials)).status_code == 401

    locked = await client.post(
        LOGIN_URL, json={"email": "owner@example.com", "password": TEST_PASSWORD}
    )
    assert locked.status_code == 429


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(ME_URL)

    assert response.status_code == 401


async def test_me_returns_current_user(owner_client: AsyncClient) -> None:
    response = await owner_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.com"
    assert response.json()["role"] == "owner"


async def test_logout_ends_session(owner_client: AsyncClient) -> None:
    response = await owner_client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert (await owner_client.get(ME_URL)).status_code == 401


async def test_admin_routes_reject_anonymous_users(client: AsyncClient) -> None:
    response = await client.get(ADMIN_URL)

    assert response.status_code == 401


async def test_admin_routes_reject_staff_users(client: AsyncClient, make_user: UserFactory) -> None:
    await make_user(email="staff@example.com", role=UserRole.STAFF)
    await client.post(LOGIN_URL, json={"email": "staff@example.com", "password": TEST_PASSWORD})

    response = await client.get(ADMIN_URL)

    assert response.status_code == 403
