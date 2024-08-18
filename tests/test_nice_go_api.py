# ruff: noqa: SLF001
from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import botocore
import pytest

from nice_go import (
    ApiError,
    AuthFailedError,
    NiceGOApi,
    NoAuthError,
    WebSocketError,
)

GET_ALL_BARRIERS_RESPONSE = {
    "data": {
        "devicesListAll": {
            "devices": [
                {
                    "state": {
                        "connectionState": {
                            "connected": True,
                            "updatedTimestamp": "1234567890",
                        },
                        "deviceId": "test_id",
                        "desired": json.dumps({"test": "value"}),
                        "reported": json.dumps({"test": "value"}),
                        "timestamp": "1234567890",
                        "version": 1,
                    },
                    "id": "test_id",
                    "type": "test_type",
                    "controlLevel": "test_control_level",
                    "attr": [{"key": "test_key", "value": "test_value"}],
                },
            ],
        },
    },
}

GET_ALL_BARRIERS_RESPONSE_NO_CONNECTION_STATE = {
    "data": {
        "devicesListAll": {
            "devices": [
                {
                    "state": {
                        "connectionState": None,
                        "deviceId": "test_id",
                        "desired": json.dumps({"test": "value"}),
                        "reported": json.dumps({"test": "value"}),
                        "timestamp": "1234567890",
                        "version": 1,
                    },
                    "id": "test_id",
                    "type": "test_type",
                    "controlLevel": "test_control_level",
                    "attr": [{"key": "test_key", "value": "test_value"}],
                },
            ],
        },
    },
}

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


async def test_schedule_event(mock_api: NiceGOApi) -> None:
    with patch("nice_go.nice_go_api.asyncio.create_task") as mock_create_task:
        coro = AsyncMock()
        mock_api._schedule_event(coro, "test_event", {"key": "value"})
        mock_create_task.assert_called_once()
        await mock_create_task.call_args[0][0]  # Await the coroutine that was scheduled


async def test_dispatch_event(mock_api: NiceGOApi) -> None:
    coro = AsyncMock()
    mock_api.on_test_event = coro  # type: ignore[attr-defined]
    mock_api._dispatch("test_event", {"key": "value"})
    await asyncio.sleep(0)  # Allow the event loop to run
    coro.assert_called_once()


async def test_authenticate(mock_api: NiceGOApi) -> None:
    with patch("nice_go.nice_go_api.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = MagicMock(
            id_token="test_token",  # noqa: S106
            refresh_token="refresh_token",  # noqa: S106
        )
        assert mock_api._session is not None
        result = await mock_api.authenticate("username", "password", mock_api._session)
        assert result == "refresh_token"
        assert mock_api.id_token == "test_token"


async def test_connect_not_authenticated(mock_api: NiceGOApi) -> None:
    mock_api.id_token = None
    with pytest.raises(NoAuthError):
        await mock_api.connect()


async def test_connect_no_endpoints(mock_api: NiceGOApi) -> None:
    mock_api.id_token = "test_token"
    mock_api._endpoints = None
    with pytest.raises(ApiError):
        await mock_api.connect()


async def test_subscribe_no_ws(mock_api: NiceGOApi) -> None:
    mock_api._ws = None
    with pytest.raises(WebSocketError):
        await mock_api.subscribe("receiver")


async def test_unsubscribe_no_ws(mock_api: NiceGOApi) -> None:
    mock_api._ws = None
    with pytest.raises(WebSocketError):
        await mock_api.unsubscribe("receiver")


async def test_get_all_barriers_not_authenticated(mock_api: NiceGOApi) -> None:
    mock_api.id_token = None
    with pytest.raises(NoAuthError):
        await mock_api.get_all_barriers()


@pytest.mark.parametrize(
    ("method_name", "query"),
    [
        ("open_barrier", "open_barrier"),
        ("close_barrier", "close_barrier"),
        ("light_on", "light_on"),
        ("light_off", "light_off"),
    ],
)
async def test_barrier_operations(
    mock_api: NiceGOApi,
    method_name: str,
    query: str,
) -> None:
    with patch("nice_go.nice_go_api.get_request_template") as mock_get_request_template:
        mock_api.id_token = "test_token"
        mock_get_request_template.return_value = {"query": query}
        assert mock_api._session is not None
        assert isinstance(mock_api._session, AsyncMock)
        mock_api._session.post.return_value.json.return_value = {
            "data": {"devicesControl": True},
        }
        method = getattr(mock_api, method_name)
        result = await method("barrier_id")
        assert result is True


async def test_event_decorator(mock_api: NiceGOApi) -> None:
    @mock_api.event
    async def on_test_event(data: dict[str, Any]) -> None:
        pass

    assert "on_test_event" in dir(mock_api)
    assert mock_api.on_test_event == on_test_event  # type: ignore[attr-defined]
    mock_api._dispatch("test_event", {})


async def test_sync_event_decorator(mock_api: NiceGOApi) -> None:
    with pytest.raises(TypeError):

        @mock_api.event  # type: ignore[type-var]
        def on_test_event(data: dict[str, Any]) -> None:
            # It's impossible for this to be called because
            # the error stops it from being added
            pass  # pragma: no cover


@pytest.mark.parametrize("error", [asyncio.CancelledError, Exception])
async def test_run_event_errors(mock_api: NiceGOApi, error: Exception) -> None:
    coro = AsyncMock()
    coro.side_effect = error
    mock_api.on_test_event = coro  # type: ignore[attr-defined]
    mock_api._dispatch("test_event", {})
    await asyncio.sleep(0)  # Allow the event loop to run
    coro.assert_called_once()


async def test_dispatch_no_listener(mock_api: NiceGOApi) -> None:
    mock_api._dispatch("test_event", {})
    await asyncio.sleep(0)  # Allow the event loop to run


async def test_authenticate_refresh(mock_api: NiceGOApi) -> None:
    with patch("nice_go.nice_go_api.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = MagicMock(
            id_token="test_token",  # noqa: S106
        )
        mock_api.id_token = "test_token"
        assert mock_api._session is not None
        await mock_api.authenticate_refresh(
            "refresh_token",
            session=mock_api._session,
        )


async def test_authenticate_botocore_client_error(mock_api: NiceGOApi) -> None:
    with patch("nice_go.nice_go_api.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.side_effect = botocore.exceptions.ClientError(
            error_response={"Error": {"Code": "TestException"}},
            operation_name="test",
        )
        assert mock_api._session is not None
        with pytest.raises(ApiError):
            await mock_api.authenticate("username", "password", mock_api._session)


async def test_authenticate_not_authorized_exception(mock_api: NiceGOApi) -> None:
    with patch("nice_go.nice_go_api.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.side_effect = botocore.exceptions.ClientError(
            error_response={"Error": {"Code": "NotAuthorizedException"}},
            operation_name="test",
        )
        assert mock_api._session is not None
        with pytest.raises(AuthFailedError):
            await mock_api.authenticate("username", "password", mock_api._session)


async def test_connect_error(mock_api: NiceGOApi) -> None:
    mock_api.id_token = "test_token"

    with patch("nice_go.nice_go_api.WebSocketClient") as mock_ws_client:
        mock_ws_client_instance = AsyncMock()
        mock_ws_client.return_value = mock_ws_client_instance
        mock_ws_client_instance.poll.side_effect = WebSocketError()
        with pytest.raises(WebSocketError):
            await mock_api.connect(reconnect=False)
        mock_ws_client_instance.connect.assert_called_once()


async def test_connect_closed(mock_api: NiceGOApi) -> None:
    mock_api.id_token = "test_token"

    with patch("nice_go.nice_go_api.WebSocketClient") as mock_ws_client:
        mock_ws_client_instance = AsyncMock()
        mock_ws_client.return_value = mock_ws_client_instance

        async def side_effect() -> None:
            mock_api._closing_task = asyncio.create_task(asyncio.sleep(0))
            await asyncio.sleep(0)
            raise WebSocketError

        mock_ws_client_instance.poll.side_effect = side_effect
        await mock_api.connect(reconnect=True)
        mock_ws_client_instance.connect.assert_called_once()


async def test_connect_reconnect(mock_api: NiceGOApi) -> None:
    mock_api.id_token = "test_token"

    with patch("nice_go.nice_go_api.WebSocketClient") as mock_ws_client:
        mock_ws_client_instance = AsyncMock()
        mock_ws_client.return_value = mock_ws_client_instance
        mock_ws_client_instance.poll.side_effect = [WebSocketError(), None]
        with suppress(StopAsyncIteration):
            await mock_api.connect(reconnect=True)
        mock_ws_client_instance.connect.assert_called_once()


async def test_subscribe(mock_api: NiceGOApi) -> None:
    mock_api.id_token = "test_token"
    mock_api._ws = AsyncMock()
    mock_api._ws.subscribe.return_value = "test_id"
    result = await mock_api.subscribe("receiver")
    assert result == "test_id"


async def test_unsubscribe(mock_api: NiceGOApi) -> None:
    mock_api.id_token = "test_token"
    mock_api._ws = AsyncMock()
    await mock_api.unsubscribe("test_id")
    mock_api._ws.unsubscribe.assert_called_once_with("test_id")


async def test_get_all_barriers(
    mock_api: NiceGOApi,
    snapshot: SnapshotAssertion,
) -> None:
    mock_api.id_token = "test_token"
    assert mock_api._session is not None
    assert isinstance(mock_api._session, AsyncMock)
    mock_api._session.post.return_value.json.return_value = GET_ALL_BARRIERS_RESPONSE
    result = await mock_api.get_all_barriers()
    # api is an object with an address that varies, so we exclude it from the snapshot
    # It's not what we're checking anyways
    # Remove the api property from all the barriers
    for barrier in result:
        barrier.api = None  # type: ignore[assignment]
    assert result == snapshot


async def test_get_all_barriers_no_connection_state(
    mock_api: NiceGOApi,
    snapshot: SnapshotAssertion,
) -> None:
    mock_api.id_token = "test_token"
    assert mock_api._session is not None
    assert isinstance(mock_api._session, AsyncMock)
    mock_api._session.post.return_value.json.return_value = (
        GET_ALL_BARRIERS_RESPONSE_NO_CONNECTION_STATE
    )
    result = await mock_api.get_all_barriers()
    for barrier in result:
        barrier.api = None  # type: ignore[assignment]

    assert result == snapshot


@pytest.mark.parametrize(
    ("method_name"),
    [
        ("open_barrier"),
        ("close_barrier"),
        ("light_on"),
        ("light_off"),
    ],
)
async def test_barrier_operations_no_auth(
    mock_api: NiceGOApi,
    method_name: str,
) -> None:
    mock_api.id_token = None
    method = getattr(mock_api, method_name)
    with pytest.raises(NoAuthError):
        await method("barrier_id")


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("authenticate", ("username", "password", None)),
        ("connect", ()),
        ("get_all_barriers", ()),
        ("open_barrier", ("barrier_id",)),
        ("close_barrier", ("barrier_id",)),
        ("light_on", ("barrier_id",)),
        ("light_off", ("barrier_id",)),
    ],
)
async def test_no_client_session(
    mock_api: NiceGOApi,
    method_name: str,
    args: tuple[str | None],
) -> None:
    mock_api._session = None
    mock_api.id_token = "test_token"
    method = getattr(mock_api, method_name)
    with pytest.raises(ValueError, match="ClientSession not provided"):
        await method(*args)


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("connect", ()),
        ("get_all_barriers", ()),
        ("open_barrier", ("barrier_id",)),
        ("close_barrier", ("barrier_id",)),
        ("light_on", ("barrier_id",)),
        ("light_off", ("barrier_id",)),
    ],
)
async def test_no_endpoints(
    mock_api: NiceGOApi,
    method_name: str,
    args: tuple[str | None],
) -> None:
    mock_api._endpoints = None
    mock_api.id_token = "test_token"
    method = getattr(mock_api, method_name)
    with pytest.raises(ApiError, match="Endpoints not available"):
        await method(*args)


async def test_auth_no_endpoints(
    mock_api: NiceGOApi,
) -> None:
    mock_api._session = AsyncMock(
        get=AsyncMock(
            return_value=AsyncMock(
                json=AsyncMock(
                    return_value={"endpoints": None},
                ),
            ),
        ),
    )

    with pytest.raises(ApiError, match="Endpoints not available"):
        await mock_api.authenticate("username", "password", mock_api._session)
