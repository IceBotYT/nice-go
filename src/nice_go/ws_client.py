from __future__ import annotations

import asyncio
import base64
import json
import uuid
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

import aiohttp

from nice_go.exceptions import WebSocketError
from nice_go.util import get_request_template

if TYPE_CHECKING:
    import yarl


class EventListener(NamedTuple):
    predicate: Callable[[dict[str, Any]], bool] | None
    event: str
    result: Callable[[dict[str, Any]], Any] | None
    future: asyncio.Future[Any]


class WebSocketClient:
    def __init__(self) -> None:
        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self._dispatch_listeners: list[EventListener] = []
        self._subscriptions: list[str] = []

    async def connect(
        self,
        client_session: aiohttp.ClientSession,
        id_token: str,
        endpoint: yarl.URL,
        dispatch: Callable[[str, dict[str, Any] | None], None],
        host: str | None = None,
    ) -> None:
        if host is None:
            msg = "host must be provided"
            raise ValueError(msg)
        self._dispatch = dispatch
        self.id_token = id_token
        self.host = host

        header_dict = {
            "Authorization": id_token,
            "host": host,
        }
        # Base64 encode the header
        header = base64.b64encode(json.dumps(header_dict).encode()).decode()
        # Construct the URL
        url = endpoint.with_query({"header": header, "payload": "e30="})

        headers = {"sec-websocket-protocol": "graphql-ws"}
        self.ws = await client_session.ws_connect(url, headers=headers)

        await self.init()

    async def init(self) -> None:
        if self.ws is None or self.ws.closed:
            msg = "WebSocket connection is closed"
            raise WebSocketError(msg)
        await self.send({"type": "connection_init"})
        try:
            message = await self.ws.receive(timeout=10)
            data = json.loads(message.data)
            if data["type"] != "connection_ack":
                msg = "Expected connection_ack, but received {}".format(data["type"])
                raise WebSocketError(
                    msg,
                )
        except asyncio.TimeoutError as e:
            msg = "Connection to the websocket server timed out"
            raise WebSocketError(msg) from e

        self._dispatch("connected", None)

    async def send(self, message: str | dict[str, Any]) -> None:
        if self.ws is None or self.ws.closed:
            msg = "WebSocket connection is closed"
            raise WebSocketError(msg)
        if isinstance(message, dict):
            await self.ws.send_json(message)
        else:
            await self.ws.send_str(message)

    async def close(self) -> None:
        if self.ws is None or self.ws.closed:
            return
        # Unsubscribe from all subscriptions
        for subscription_id in self._subscriptions:
            await self.unsubscribe(subscription_id)
        await self.ws.close()

    async def poll(self) -> None:
        if self.ws is None or self.ws.closed:
            error_msg = "WebSocket connection is closed"
            raise WebSocketError(error_msg)
        msg = await self.ws.receive(timeout=60.0)
        if msg.type == aiohttp.WSMsgType.TEXT:
            await self.received_message(msg.data)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            error_msg = f"WebSocket connection closed with error {msg}"
            raise WebSocketError(error_msg)
        elif msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.CLOSED,
        ):
            error_msg = "WebSocket connection closed"
            raise WebSocketError(error_msg)

    def load_message(self, message: str) -> Any:
        try:
            parsed_message = json.loads(message)
        except json.JSONDecodeError as e:
            msg = f"Received invalid JSON message: {message}"
            raise WebSocketError(msg) from e

        return parsed_message

    def dispatch_message(self, message: dict[str, Any]) -> None:
        if message["type"] == "data":
            self._dispatch(message["type"], message["payload"])
        elif message["type"] == "error":
            msg = f"Received error message: {message}"
            raise WebSocketError(msg)

    async def received_message(self, message: str) -> None:
        parsed_message = self.load_message(message)
        self.dispatch_message(parsed_message)

        removed = []
        for index, entry in enumerate(self._dispatch_listeners):
            if entry.event != parsed_message["type"]:
                continue

            future = entry.future
            if future.cancelled():
                removed.append(index)
                continue

            if entry.predicate is not None:
                try:
                    valid = entry.predicate(parsed_message)
                except Exception as e:  # noqa: BLE001
                    future.set_exception(e)
                    removed.append(index)
                    continue
            else:
                valid = True

            if valid:
                ret = (
                    parsed_message
                    if entry.result is None
                    else entry.result(parsed_message)
                )
                future.set_result(ret)
                removed.append(index)

        for index in reversed(removed):
            del self._dispatch_listeners[index]

    def wait_for(
        self,
        event: str,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
        result: Callable[[dict[str, Any]], Any] | None = None,
    ) -> asyncio.Future[Any]:
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._dispatch_listeners.append(EventListener(predicate, event, result, future))
        return future

    async def subscribe(self, receiver: str) -> str:
        subscription_id = str(uuid.uuid4())
        payload = await get_request_template(
            "subscribe",
            {
                "receiver_id": receiver,
                "uuid": subscription_id,
                "id_token": self.id_token,
                "host": self.host,
            },
        )
        await self.send(payload)

        def _predicate(message: dict[str, Any]) -> bool:
            if "type" not in message:
                return False
            if "id" not in message:
                return False
            valid: bool = (
                message["type"] == "start_ack" and message["id"] == subscription_id
            )
            return valid

        try:
            await asyncio.wait_for(self.wait_for("start_ack", _predicate), timeout=10)
        except asyncio.TimeoutError as e:
            msg = "Subscription to the websocket server timed out"
            raise WebSocketError(msg) from e

        self._subscriptions.append(subscription_id)

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        payload = await get_request_template("unsubscribe", {"id": subscription_id})
        await self.send(payload)
        self._subscriptions.remove(subscription_id)

    @property
    def closed(self) -> bool:
        if self.ws is None:
            return True
        return self.ws.closed
