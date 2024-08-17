# ruff: noqa: SLF001
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import yarl

from nice_go import WebSocketError
from nice_go._ws_client import EventListener, WebSocketClient


async def test_ws_connect(mock_ws_client: WebSocketClient) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_session = MagicMock()
    mock_session.ws_connect = AsyncMock()
    mock_session.ws_connect.return_value = AsyncMock(closed=False)
    mock_session.ws_connect.return_value.receive = AsyncMock()
    mock_session.ws_connect.return_value.receive.return_value = MagicMock(
        data=json.dumps({"type": "connection_ack"}),
    )
    mock_ws_client._dispatch = MagicMock()
    await mock_ws_client.connect(
        mock_session,
        "test_token",
        yarl.URL("wss://test_endpoint"),
        MagicMock(),
        "test_host",
    )
    mock_session.ws_connect.assert_called_once()
    mock_ws_client._dispatch.assert_called_once()
    mock_ws_client.ws.receive.assert_called_once()
    mock_ws_client.ws.send_json.assert_called_once()


async def test_ws_init_unexpected_type(mock_ws_client: WebSocketClient) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_ws_client.ws.receive = AsyncMock()
    mock_ws_client.ws.receive.return_value = MagicMock(
        data=json.dumps({"type": "unexpected_type"}),
    )
    with pytest.raises(WebSocketError):
        await mock_ws_client.init()


async def test_ws_init_timeout(mock_ws_client: WebSocketClient) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_ws_client.ws.receive = AsyncMock()
    mock_ws_client.ws.receive.side_effect = asyncio.TimeoutError
    with pytest.raises(WebSocketError):
        await mock_ws_client.init()


async def test_ws_send_json(mock_ws_client: WebSocketClient) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_ws_client.ws.send_json = AsyncMock()
    await mock_ws_client.send({"type": "test_type"})
    mock_ws_client.ws.send_json.assert_called_once()


async def test_ws_send_str(mock_ws_client: WebSocketClient) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_ws_client.ws.send_str = AsyncMock()  # sourcery skip: name-type-suffix
    await mock_ws_client.send("test_message")
    mock_ws_client.ws.send_str.assert_called_once()


async def test_ws_subscribe_and_close(mock_ws_client: WebSocketClient) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    # Test both subscribing and closing, as they are closely related
    mock_ws_client.ws.send_json = AsyncMock()
    mock_ws_client.ws.close = AsyncMock()
    mock_ws_client.ws.receive = AsyncMock()

    subscription_id = "test_id"
    mock_ws_client.ws.receive.return_value = MagicMock(
        data=json.dumps({"id": subscription_id, "type": "start_ack"}),
        type=aiohttp.WSMsgType.TEXT,
    )

    with patch("nice_go._ws_client.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = subscription_id
        subscribe_task = asyncio.create_task(mock_ws_client.subscribe("test_query"))
        await asyncio.sleep(0.1)
        mock_ws_client.ws.send_json.assert_called_once()
        await mock_ws_client.poll()
        await subscribe_task
        await mock_ws_client.close()
        call_count_should_be = 2
        assert mock_ws_client.ws.send_json.call_count == call_count_should_be
        mock_ws_client.ws.close.assert_called_once()


@pytest.mark.parametrize(
    "msg_type",
    [
        aiohttp.WSMsgType.ERROR,
        aiohttp.WSMsgType.CLOSE,
        aiohttp.WSMsgType.CLOSING,
        aiohttp.WSMsgType.CLOSED,
    ],
)
async def test_ws_poll_errors(
    mock_ws_client: WebSocketClient,
    msg_type: aiohttp.WSMsgType,
) -> None:
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_ws_client.ws.receive = AsyncMock()
    mock_ws_client.ws.receive.return_value = MagicMock(type=msg_type)
    with pytest.raises(WebSocketError):
        await mock_ws_client.poll()


async def test_ws_received_message(mock_ws_client: WebSocketClient) -> None:
    mock_ws_client._dispatch = MagicMock()
    await mock_ws_client.received_message(
        json.dumps({"type": "data", "payload": "test_payload"}),
    )
    mock_ws_client._dispatch.assert_called_once()

    with pytest.raises(WebSocketError):
        await mock_ws_client.received_message(json.dumps({"type": "error"}))

    with pytest.raises(WebSocketError):
        await mock_ws_client.received_message("invalid_json")


async def test_ws_received_message_dispatch_listener_skip_type(
    mock_ws_client: WebSocketClient,
) -> None:
    mock_ws_client._dispatch_listeners = [
        EventListener(
            predicate=AsyncMock(return_value=True),
            event="wrong_type",
            future=MagicMock(),
            result=MagicMock(),
        ),
    ]
    await mock_ws_client.received_message(
        json.dumps({"type": "data", "payload": "test_payload"}),
    )
    assert len(mock_ws_client._dispatch_listeners) == 1


async def test_ws_received_message_dispatch_listener_cancelled(
    mock_ws_client: WebSocketClient,
) -> None:
    mock_ws_client._dispatch_listeners = [
        EventListener(
            predicate=AsyncMock(return_value=True),
            event="data",
            future=MagicMock(cancelled=MagicMock(return_value=True)),
            result=MagicMock(),
        ),
    ]
    await mock_ws_client.received_message(
        json.dumps({"type": "data", "payload": "test_payload"}),
    )
    assert not mock_ws_client._dispatch_listeners


async def test_ws_received_message_dispatch_listener_predicate_exception(
    mock_ws_client: WebSocketClient,
) -> None:
    mock_ws_client._dispatch_listeners = [
        EventListener(
            predicate=MagicMock(side_effect=Exception),
            event="data",
            future=MagicMock(cancelled=MagicMock(return_value=False)),
            result=MagicMock(),
        ),
    ]
    await mock_ws_client.received_message(
        json.dumps({"type": "data", "payload": "test_payload"}),
    )
    assert not mock_ws_client._dispatch_listeners


async def test_subscribe_timeout(mock_ws_client: WebSocketClient) -> None:
    with patch("nice_go._ws_client.asyncio.wait_for") as mock_wait_for:
        mock_wait_for.side_effect = asyncio.TimeoutError
    with pytest.raises(WebSocketError):
        await mock_ws_client.subscribe("test_query")


async def test_unsubscribe(mock_ws_client: WebSocketClient) -> None:
    mock_ws_client._subscriptions = ["test_id"]
    assert mock_ws_client.ws is not None
    assert isinstance(mock_ws_client.ws, AsyncMock)
    mock_ws_client.ws.send_json = AsyncMock()
    await mock_ws_client.unsubscribe("test_id")
    mock_ws_client.ws.send_json.assert_called_once()
    assert "test_id" not in mock_ws_client._subscriptions
    assert mock_ws_client.ws.send_json.call_args[0][0] == {
        "id": "test_id",
        "type": "stop",
    }


async def test_closed_property(mock_ws_client: WebSocketClient) -> None:
    assert not mock_ws_client.closed
    mock_ws_client.ws = MagicMock()
    mock_ws_client.ws.closed = True
    assert mock_ws_client.closed


async def test_connect_no_host(mock_ws_client: WebSocketClient) -> None:
    with pytest.raises(ValueError, match="host must be provided"):
        await mock_ws_client.connect(
            MagicMock(),
            "test_token",
            yarl.URL("wss://test_endpoint"),
            MagicMock(),
            None,
        )


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("init", ()),
        ("send", ({"type": "test_type"},)),
        ("poll", ()),
    ],
)
async def test_closed_error(
    mock_ws_client: WebSocketClient,
    method: str,
    args: tuple[dict[str, str] | None],
) -> None:
    mock_ws_client.ws = None
    with pytest.raises(WebSocketError, match="WebSocket connection is closed"):
        await getattr(mock_ws_client, method)(*args)


async def test_close_already_closed(
    mock_ws_client: WebSocketClient,
) -> None:
    mock_ws_client.ws = MagicMock()
    mock_ws_client.ws.closed = True
    await mock_ws_client.close()
    assert mock_ws_client.ws.close.call_count == 0


async def test_received_message_no_predicate(
    mock_ws_client: WebSocketClient,
) -> None:
    mock_ws_client._dispatch_listeners = [
        EventListener(
            predicate=None,
            event="data",
            future=MagicMock(cancelled=MagicMock(return_value=False)),
            result=MagicMock(),
        ),
    ]
    await mock_ws_client.received_message(
        json.dumps({"type": "data", "payload": "test_payload"}),
    )
    assert not mock_ws_client._dispatch_listeners


async def test_received_message_type_or_payload_missing(
    mock_ws_client: WebSocketClient,
) -> None:
    with pytest.raises(WebSocketError):
        await mock_ws_client.received_message(json.dumps({"payload": "test_payload"}))
