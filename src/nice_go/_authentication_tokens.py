"""Holds the tokens retrieved from authentication."""

from __future__ import annotations


class AuthenticationTokens:
    """
    A class to handle authentication tokens.

    Initializes an AuthenticationTokens object with the provided data dictionary. It
    extracts the 'IdToken' and 'RefreshToken' if available, storing them as attributes.

    Args:
        data (dict[str, str]): A dictionary containing authentication tokens.

    Attributes:
        id_token (str): The IdToken retrieved from authentication.
        refresh_token (str | None): The RefreshToken retrieved from authentication. If
            no RefreshToken is available, it is set to None.

    """

    def __init__(self, data: dict[str, str]) -> None:
        """Initialize the AuthenticationTokens object."""
        self.id_token = data["IdToken"]
        self.refresh_token: str | None = None
        try:
            self.refresh_token = data["RefreshToken"]
        except KeyError:
            self.refresh_token = None
