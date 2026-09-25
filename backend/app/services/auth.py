from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository

INVALID_CREDENTIALS = "Email ou mot de passe incorrect."

_DUMMY_HASH = hash_password("dummy-password-for-timing-protection")


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)

        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise AuthenticationError(INVALID_CREDENTIALS)

        if not verify_password(password, user.hashed_password) or not user.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)

        user.last_login_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_active_user(self, user_id: int) -> User:
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Session invalide ou expirée.")
        return user
