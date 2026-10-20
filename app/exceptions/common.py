
from app.exceptions.base import AppException


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""


class ConflictError(AppException):
    """Raised when a request conflicts with existing data."""


class ValidationError(AppException):
    """Raised when application-level business validation fails."""


class UnauthorizedError(AppException):
    """Raised when authentication is required or invalid."""


class ForbiddenError(AppException):
    """Raised when a user lacks permission to perform an action."""
