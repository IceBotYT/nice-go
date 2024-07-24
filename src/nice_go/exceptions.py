class NiceGOError(Exception):
    """Base exception for Nice G.O. API"""


class NoAuthError(NiceGOError):
    """Not authenticated exception."""


class ApiError(NiceGOError):
    """Api error."""


class AuthFailedError(NiceGOError):
    """Authentication failed."""


class WebSocketError(NiceGOError):
    """Websocket error."""
