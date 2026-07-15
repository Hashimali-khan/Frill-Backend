class AppError(Exception):
    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class InvalidTokenError(AppError):
    status_code = 401
    detail = "Invalid or expired session"


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class ForbiddenError(AppError):
    status_code = 403
    detail = "You don't have permission to do this"


class ConflictError(AppError):
    status_code = 409
    detail = "Conflict with existing data"


class ValidationAppError(AppError):
    status_code = 422
    detail = "Invalid input"