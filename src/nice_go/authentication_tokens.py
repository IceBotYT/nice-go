""" " Holds the tokens retrieved from authentication."""

from __future__ import annotations


class AuthenticationTokens:
    def __init__(self, data: dict[str, str]) -> None:
        self.id_token = data["IdToken"]
        self.refresh_token: str | None = None
        try:
            self.refresh_token = data["RefreshToken"]
        except KeyError:
            self.refresh_token = None
