"""Fixtures for tests."""

# ruff: noqa: SLF001

from unittest.mock import AsyncMock, MagicMock

import pytest
from tenacity import wait_none

from nice_go._aws_cognito_authenticator import AwsCognitoAuthenticator
from nice_go._ws_client import WebSocketClient
from nice_go.nice_go_api import NiceGOApi


@pytest.fixture
def mock_api() -> NiceGOApi:
    """Mocked NiceGOApi instance."""
    api = NiceGOApi()
    api._session = AsyncMock()
    api._device_ws = AsyncMock()
    api._endpoints = {
        "GraphQL": {
            "device": {
                "wss": "wss://test",
                "https": "https://test",
            },
            "events": {
                "wss": "wss://test",
                "https": "https://test",
            },
        },
    }
    api.connect.retry.wait = wait_none()  # type: ignore[attr-defined]
    return api


@pytest.fixture
def mock_ws_client() -> WebSocketClient:
    """Mocked WebSocketClient instance."""
    ws = WebSocketClient(client_session=MagicMock())
    ws.ws = AsyncMock(closed=False)
    ws._dispatch = MagicMock()
    ws.id_token = "test_token"
    ws.host = "test_host"
    return ws


@pytest.fixture
def mock_authenticator() -> AwsCognitoAuthenticator:
    """Mocked AwsCognitoAuthenticator instance."""
    return AwsCognitoAuthenticator(
        "test_region",
        "test_client_id",
        "test_pool_id",
        "test_identity_pool_id",
    )
