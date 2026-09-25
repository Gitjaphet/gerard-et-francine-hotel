from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import SESSION_COOKIE, CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


ServiceDep = Annotated[AuthService, Depends(get_auth_service)]


class CookieOptions(TypedDict):
    httponly: bool
    secure: bool
    samesite: Literal["lax", "strict", "none"]
    path: str


def _cookie_options() -> CookieOptions:
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.app_env != "development",
        "samesite": "lax",
        "path": "/",
    }


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    service: ServiceDep,
) -> UserRead:
    ip_address = request.client.host if request.client else "unknown"
    user = await service.authenticate(data.email, data.password, ip_address)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_access_token(str(user.id)),
        max_age=get_settings().access_token_expire_minutes * 60,
        **_cookie_options(),
    )
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, **_cookie_options())


@router.get("/me")
async def read_current_user(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
