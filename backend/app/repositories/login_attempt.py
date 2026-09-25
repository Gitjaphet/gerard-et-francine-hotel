from datetime import datetime

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_attempt import LoginAttempt


class LoginAttemptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, *, email: str, ip_address: str, succeeded: bool) -> None:
        self.db.add(LoginAttempt(email=email, ip_address=ip_address, succeeded=succeeded))
        await self.db.flush()

    async def count_failures_by_email(self, email: str, since: datetime) -> int:
        return await self._count_failures(LoginAttempt.email == email, since)

    async def count_failures_by_ip(self, ip_address: str, since: datetime) -> int:
        return await self._count_failures(LoginAttempt.ip_address == ip_address, since)

    async def _count_failures(self, condition: ColumnElement[bool], since: datetime) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(LoginAttempt)
            .where(condition, LoginAttempt.succeeded.is_(False), LoginAttempt.created_at >= since)
        )
        return result.scalar_one()

    async def delete_failures_by_email(self, email: str, since: datetime) -> int:
        result = await self.db.execute(
            delete(LoginAttempt).where(
                LoginAttempt.email == email,
                LoginAttempt.succeeded.is_(False),
                LoginAttempt.created_at >= since,
            )
        )
        return result.rowcount
