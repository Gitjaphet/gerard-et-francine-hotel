class AppError(Exception):
    """Erreur métier de base. Les routes la traduisent en réponse HTTP."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class PermissionDeniedError(AppError):
    pass


class TooManyAttemptsError(AppError):
    pass
