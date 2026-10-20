
class AppException(Exception):
    """Base class for application-level exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
