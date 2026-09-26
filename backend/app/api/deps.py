from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.roles import UserRole
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth import AuthService

SESSION_COOKIE = "gf_admin_session"

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if not token:
        raise AuthenticationError("Authentification requise.")
    subject = decode_access_token(token)
    if subject is None or not subject.isdigit():
        raise AuthenticationError("Session invalide ou expirée.")
    return await AuthService(db).get_active_user(int(subject))


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("Vous n'avez pas les droits nécessaires.")
        return user

    return checker


OwnerOnly = Depends(require_roles(UserRole.OWNER))
OwnerOrStaff = Depends(require_roles(UserRole.OWNER, UserRole.STAFF))


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
