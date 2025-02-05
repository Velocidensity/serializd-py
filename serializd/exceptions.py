class SerializdError(Exception):
    """Main exception class"""

    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self) -> str:
        return self.message or ''


class LoginError(SerializdError):
    """Failed to log in error"""


class InvalidTokenError(SerializdError):
    """Invalid token provided error"""


class EmptySeasonError(SerializdError):
    """Empty season info returned error"""
