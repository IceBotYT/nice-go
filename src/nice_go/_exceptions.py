"""Exceptions for Nice G.O. API."""


class NiceGOError(Exception):
    """Base exception for Nice G.O. API."""


class NoAuthError(NiceGOError):
    """Not authenticated exception."""


class ApiError(NiceGOError):
    """API error."""


class AuthFailedError(NiceGOError):
    """Authentication failed. Check your credentials."""


class WebSocketError(NiceGOError):
    """WebSocket error."""


class ReconnectWebSocketError(WebSocketError):
    """Reconnect WebSocket error."""
