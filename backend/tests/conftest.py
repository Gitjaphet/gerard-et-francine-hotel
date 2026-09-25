"""Configuration commune des tests.

Les variables d'environnement sont définies AVANT tout import de l'application :
la configuration et l'engine SQLAlchemy sont créés au premier import, ils doivent
donc voir la base de test et non la base de développement.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://hotel:hotel@localhost:5432/hotel_test",
)
os.environ["APP_ENV"] = "development"
os.environ["APP_DEBUG"] = "false"
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-automated-tests-only")

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.roles import UserRole
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User

if not os.environ["DATABASE_URL"].endswith("_test"):
    raise RuntimeError("Les tests doivent tourner sur une base dont le nom finit par _test.")


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> Iterator[None]:
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(scope="session", autouse=True)
async def dispose_engine() -> AsyncIterator[None]:
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    yield
    tables = ", ".join(table.name for table in reversed(Base.metadata.sorted_tables))
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


TEST_PASSWORD = "correct-horse-battery-staple"

UserFactory = Callable[..., Awaitable[User]]


@pytest.fixture
def make_user() -> UserFactory:
    async def factory(
        email: str = "owner@example.com",
        role: UserRole = UserRole.OWNER,
        is_active: bool = True,
    ) -> User:
        async with AsyncSessionLocal() as db:
            user = User(
                email=email,
                full_name="Test User",
                role=role,
                is_active=is_active,
                hashed_password=hash_password(TEST_PASSWORD),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    return factory


@pytest.fixture
async def owner_client(client: AsyncClient, make_user: UserFactory) -> AsyncClient:
    user = await make_user()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return client
