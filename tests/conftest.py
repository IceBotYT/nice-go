from unittest.mock import AsyncMock, MagicMock

import pytest
from nice_go.aws_cognito_authenticator import AwsCognitoAuthenticator
from nice_go.nice_go_api import NiceGOApi
from nice_go.ws_client import WebSocketClient


@pytest.fixture()
def mock_api() -> NiceGOApi:
    api = NiceGOApi()
    api.session = AsyncMock()
    api.authenticator = MagicMock()
    api.ws = AsyncMock()
    api.endpoints = {
        "GraphQL": {"device": {"wss": "wss://test", "https": "https://test"}},
    }
    return api


@pytest.fixture()
def mock_ws_client() -> WebSocketClient:
    ws = WebSocketClient()
    ws.ws = MagicMock(closed=False)
    ws._dispatch = MagicMock()  # noqa: SLF001
    ws.id_token = "test_token"
    ws.host = "test_host"
    return ws


@pytest.fixture()
def mock_authenticator() -> AwsCognitoAuthenticator:
    return AwsCognitoAuthenticator(
        "test_region",
        "test_client_id",
        "test_pool_id",
        "test_identity_pool_id",
    )
