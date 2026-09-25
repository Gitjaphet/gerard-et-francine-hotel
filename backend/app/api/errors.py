from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError, ConflictError, NotFoundError

STATUS_CODES: dict[type[AppError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        status_code = STATUS_CODES.get(type(exc), 400)
        return JSONResponse(status_code=status_code, content={"detail": exc.message})
