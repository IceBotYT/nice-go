"""This module contains the WebSocketClient class, which is used to interact with the
WebSocket server.

Classes:
    WebSocketClient: A class that represents a WebSocket client.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

import aiohttp

from nice_go._exceptions import ReconnectWebSocketError, WebSocketError
from nice_go._util import get_request_template

if TYPE_CHECKING:
    import yarl

_LOGGER = logging.getLogger(__name__)


class EventListener(NamedTuple):
    """A class representing an event listener."""

    predicate: Callable[[dict[str, Any]], bool] | None
    event: str
    result: Callable[[dict[str, Any]], Any] | None
    future: asyncio.Future[Any]


class WebSocketClient:
    """A class that represents a WebSocket client.

    Attributes:
        ws (aiohttp.ClientWebSocketResponse | None): The WebSocket connection.
        _dispatch_listeners (list[EventListener]): A list of event listeners.
        _subscriptions (list[str]): A list of subscription IDs.
    """

    def __init__(self, client_session: aiohttp.ClientSession) -> None:
        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self._dispatch_listeners: list[EventListener] = []
        self._subscriptions: list[str] = []
        self.client_session = client_session

    def _redact_message(self, message: str | dict[str, Any]) -> Any:
        """Redact sensitive information from a message.

        Args:
            message: The message to redact.

        Returns:
            The redacted message.
        """
        if isinstance(message, dict):
            return json.loads(json.dumps(message).replace(self.id_token, "<REDACTED>"))
        return message.replace(self.id_token, "<REDACTED>")

    async def _watch_keepalive(self) -> None:
        """A task that handles the timeout for the WebSocket connection.

        Raises:
            WebSocketError: If the WebSocket connection is closed.
        """
        if self.ws is None or self.ws.closed:
            msg = "WebSocket connection is closed"
            raise WebSocketError(msg)
        await asyncio.sleep(self._timeout / 1000)
        _LOGGER.debug("WebSocket keepalive timeout reached, reconnecting")
        await self._reconnect()

    async def _reconnect(self) -> None:
        """Reconnect to the WebSocket server.

        Raises:
            WebSocketError: If the WebSocket connection is closed or an error occurs.
        """
        if self.ws is None or self.ws.closed:
            msg = "WebSocket connection is closed"
            raise WebSocketError(msg)
        _LOGGER.debug("Reconnecting to WebSocket server")
        await self.close()
        raise ReconnectWebSocketError

    async def connect(
        self,
        id_token: str,
        endpoint: yarl.URL,
        api_type: str,
        dispatch: Callable[[str, dict[str, Any] | None], None],
        host: str | None = None,
    ) -> None:
        """Connect to the WebSocket server.

        Args:
            client_session: The aiohttp ClientSession.
            id_token: The IdToken retrieved from authentication.
            endpoint: The endpoint URL.
            dispatch: The dispatch function.
            host: The host URL.

        Raises:
            ValueError: If host is not provided.
            WebSocketError: If the WebSocket connection is closed or an error occurs.
        """
        if host is None:
            msg = "host must be provided"
            raise ValueError(msg)

        self._dispatch = dispatch
        self.id_token = id_token
        self.host = host
        self.api_type = api_type  # Should be "device" or "events"
        self._endpoint = endpoint

        raw_header = {
            "Authorization": id_token,
            "host": host,
        }
        # Base64 encode the header
        header = base64.b64encode(json.dumps(raw_header).encode()).decode()
        # Construct the URL
        url = endpoint.with_query({"header": header, "payload": "e30="})

        # URL contains sensitive information, so we don't want to log it
        _LOGGER.debug("Connecting to WebSocket server at %s", endpoint)

        headers = {"sec-websocket-protocol": "graphql-ws"}
        self.ws = await self.client_session.ws_connect(url, headers=headers)

        await self.init()

    async def init(self) -> None:
        """Initialize the WebSocket connection.

        Raises:
            WebSocketError: If the WebSocket connection is closed or an error occurs.
        """
        if self.ws is None or self.ws.closed:
            msg = "WebSocket connection is closed"
            raise WebSocketError(msg)
        _LOGGER.debug("Initializing WebSocket connection")
        await self.send({"type": "connection_init"})
        try:
            _LOGGER.debug("Waiting for connection_ack")
            message = await self.ws.receive(timeout=10)
            data = json.loads(message.data)
            if data["type"] != "connection_ack":
                msg = f'Expected connection_ack, but received {data["type"]}'
                raise WebSocketError(
                    msg,
                )
        except asyncio.TimeoutError as e:
            msg = "Connection to the websocket server timed out"
            raise WebSocketError(msg) from e
        _LOGGER.debug("Received connection_ack, WebSocket connection established")

        self._timeout = data.get("payload", {}).get("timeout", 300000)
        self._timeout_task = asyncio.create_task(self._watch_keepalive())
        self._dispatch(f"{self.api_type}_connected", None)

    async def send(self, message: str | dict[str, Any]) -> None:
        """Send a message to the WebSocket server.

        Args:
            message: The message to send.

        Raises:
            WebSocketError: If the WebSocket connection is closed
        """
        if self.ws is None or self.ws.closed:
            msg = "WebSocket connection is closed"
            raise WebSocketError(msg)
        redacted_message = self._redact_message(message)
        _LOGGER.debug("Sending message: %s", redacted_message)
        if isinstance(message, dict):
            await self.ws.send_json(message)
        else:
            await self.ws.send_str(message)

    async def close(self) -> None:
        """Close the WebSocket connection.

        Raises:
            WebSocketError: If the WebSocket connection is closed
        """
        if self.ws is None or self.ws.closed:
            return
        _LOGGER.debug("Closing WebSocket client")
        # Unsubscribe from all subscriptions
        for subscription_id in self._subscriptions:
            _LOGGER.debug("Unsubscribing from subscription %s", subscription_id)
            await self.unsubscribe(subscription_id)
        # Cancel the keepalive task
        self._timeout_task.cancel()
        try:
            await self._timeout_task
        except asyncio.CancelledError:
            _LOGGER.debug("Keepalive task was cancelled")
        except Exception:
            _LOGGER.exception("Exception occurred while cancelling keepalive task")
        _LOGGER.debug("Closing WebSocket connection")
        await self.ws.close()
        _LOGGER.debug("WebSocket connection closed")

    async def poll(self) -> None:
        """Poll the WebSocket connection for messages.

        Raises:
            WebSocketError: If the WebSocket connection is closed or an error occurs.
        """
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
            # Cancel the keepalive task
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                _LOGGER.debug("Keepalive task was cancelled")
            except Exception:
                _LOGGER.exception("Exception occurred while cancelling keepalive task")
            raise WebSocketError(error_msg)

    def load_message(self, message: str) -> Any:
        """Load a message from a string.

        Args:
            message: The message to load.

        Returns:
            The parsed message.

        Raises:
            WebSocketError: If the message is not valid JSON.
        """
        try:
            parsed_message = json.loads(message)
        except json.JSONDecodeError as e:
            msg = f"Received invalid JSON message: {message}"
            raise WebSocketError(msg) from e

        return parsed_message

    def dispatch_message(self, message: dict[str, Any]) -> None:
        """Dispatch a message to the appropriate handler.

        Args:
            message: The message to dispatch.

        Raises:
            WebSocketError: If the message type is not valid.
        """
        if message["type"] == "data":
            if self.api_type == "events" and message["payload"]["data"]["eventsFeed"][
                "item"
            ]["eventId"] == ("event-error-barrier-obstructed"):
                self._dispatch(
                    "barrier_obstructed",
                    message["payload"]["data"]["eventsFeed"]["item"],
                )
            if self.api_type == "events":
                return

            self._dispatch(message["type"], message["payload"])
        elif message["type"] == "error":
            msg = f"Received error message: {message}"
            raise WebSocketError(msg)
        elif message["type"] == "ka":
            _LOGGER.debug("Received keepalive message")
            # Restart the keepalive task
            self._timeout_task.cancel()
            self._timeout_task = asyncio.create_task(self._watch_keepalive())
        else:
            _LOGGER.debug("Received message of type %s: %s", message["type"], message)

    async def received_message(self, message: str) -> None:
        """Handle a received message.

        Args:
            message: The message to handle.

        Raises:
            WebSocketError: If the message does not contain 'type
        """
        _LOGGER.debug("Received message: %s", message)
        parsed_message = self.load_message(message)
        if "type" not in message:
            msg = f"Received message does not contain 'type', got {message}"
            raise WebSocketError(msg)
        _LOGGER.debug("Dispatching message")
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

                _LOGGER.debug("Event %s occurred, no longer waiting", entry.event)

        for index in reversed(removed):
            del self._dispatch_listeners[index]

    def wait_for(
        self,
        event: str,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
        result: Callable[[dict[str, Any]], Any] | None = None,
    ) -> asyncio.Future[Any]:
        """Wait for an event to occur.

        Args:
            event: The event to wait for.
            predicate: A predicate function.
            result: A result function.

        Returns:
            A future that resolves when the event occurs.

        Raises:
            WebSocketError: If the event is not valid.
        """
        _LOGGER.debug("Waiting for event %s", event)
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._dispatch_listeners.append(EventListener(predicate, event, result, future))
        return future

    async def subscribe(self, receiver: str) -> str:
        """Subscribe to the WebSocket server.

        Args:
            receiver: The receiver ID. Typically, it's the organization ID, which can be
                found in the attributes of any barrier. (Don't ask me why.)

        Returns:
            The subscription ID.

        Raises:
            WebSocketError: If the subscription times out.
        """
        subscription_id = str(uuid.uuid4())
        payload = await get_request_template(
            "subscribe" if self.api_type == "device" else "event_subscribe",
            {
                "receiver_id": receiver,
                "uuid": subscription_id,
                "id_token": self.id_token,
                "host": self.host,
            },
        )
        _LOGGER.debug(
            "Subscribing to receiver %s with subscription ID %s",
            receiver,
            subscription_id,
        )
        await self.send(payload)

        def _predicate(message: dict[str, Any]) -> bool:
            valid: bool = (
                message["type"] == "start_ack" and message["id"] == subscription_id
            )
            _LOGGER.debug("Checking if start_ack is valid: %s", valid)
            return valid

        try:
            await asyncio.wait_for(self.wait_for("start_ack", _predicate), timeout=10)
        except asyncio.TimeoutError as e:
            msg = "Subscription to the websocket server timed out"
            raise WebSocketError(msg) from e

        _LOGGER.debug("Subscription successful")

        self._subscriptions.append(subscription_id)

        _LOGGER.debug("Subscription added")

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from the WebSocket server.

        Args:
            subscription_id: The subscription ID.

        Raises:
            WebSocketError: If the WebSocket connection is closed
        """
        try:
            self._subscriptions.remove(subscription_id)
        except ValueError:
            _LOGGER.debug("Subscription %s not found", subscription_id)
            return
        finally:
            _LOGGER.debug("Removing subscription %s", subscription_id)
            payload = await get_request_template("unsubscribe", {"id": subscription_id})
            _LOGGER.debug("Unsubscribing from subscription %s", subscription_id)
            await self.send(payload)
            _LOGGER.debug("Unsubscribed from subscription %s", subscription_id)

    @property
    def closed(self) -> bool:
        """Check if the WebSocket connection is closed.

        Returns:
            True if the WebSocket connection is closed, False otherwise.
        """
        return True if self.ws is None else self.ws.closed
