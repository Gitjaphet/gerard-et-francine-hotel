from datetime import UTC, datetime, timedelta
from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, TooManyAttemptsError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user import UserRepository

INVALID_CREDENTIALS = "Email ou mot de passe incorrect."
TOO_MANY_ATTEMPTS = "Trop de tentatives de connexion. Réessayez dans 15 minutes."

LOCKOUT_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_EMAIL = 5
MAX_FAILURES_PER_IP = 20

_DUMMY_HASH = hash_password("dummy-password-for-timing-protection")


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.attempts = LoginAttemptRepository(db)

    async def authenticate(self, email: str, password: str, ip_address: str) -> User:
        email = email.strip().lower()
        await self._ensure_not_locked(email, ip_address)

        user = await self.users.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            await self._record_failure(email, ip_address)

        if not verify_password(password, user.hashed_password) or not user.is_active:
            await self._record_failure(email, ip_address)

        await self.attempts.add(email=email, ip_address=ip_address, succeeded=True)
        user.last_login_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_active_user(self, user_id: int) -> User:
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Session invalide ou expirée.")
        return user

    async def _ensure_not_locked(self, email: str, ip_address: str) -> None:
        since = datetime.now(UTC) - LOCKOUT_WINDOW
        if (
            await self.attempts.count_failures_by_email(email, since) >= MAX_FAILURES_PER_EMAIL
            or await self.attempts.count_failures_by_ip(ip_address, since) >= MAX_FAILURES_PER_IP
        ):
            raise TooManyAttemptsError(TOO_MANY_ATTEMPTS)

    async def _record_failure(self, email: str, ip_address: str) -> NoReturn:
        await self.attempts.add(email=email, ip_address=ip_address, succeeded=False)
        await self.db.commit()
        raise AuthenticationError(INVALID_CREDENTIALS)
