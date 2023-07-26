class SerializdError(Exception):
    """Main exception class"""
    def __init__(self, message: str | None = None):
        self.message = message

    def __str__(self) -> str:
        return self.message or ''


class RequestError(SerializdError):
    """HTTP request not successful error"""


class ParseError(SerializdError):
    """JSON response parse error"""


class LoginError(SerializdError):
    """Unspecified login error"""


class InvalidTokenError(SerializdError):
    """Invalid token provided error"""
