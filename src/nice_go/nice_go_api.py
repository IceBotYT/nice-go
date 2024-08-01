# sourcery skip: avoid-single-character-names-variables
"""Parses data from the Nice G.O. API.

This module provides a class to interact
with the Nice G.O. API. It allows the user
to authenticate, connect to the WebSocket
API, and interact with barriers.

Classes:
    NiceGOApi: A class to interact with the Nice G.O. API.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, TypeVar

import aiohttp
import botocore
import yarl

from nice_go._aws_cognito_authenticator import AwsCognitoAuthenticator
from nice_go._backoff import ExponentialBackoff
from nice_go._barrier import Barrier, BarrierState, ConnectionState
from nice_go._const import (
    CLIENT_ID,
    ENDPOINTS_URL,
    IDENTITY_POOL_ID,
    POOL_ID,
    REGION_NAME,
)
from nice_go._exceptions import (
    ApiError,
    AuthFailedError,
    NoAuthError,
    WebSocketError,
)
from nice_go._util import get_request_template
from nice_go._ws_client import WebSocketClient

T = TypeVar("T")
Coro = Coroutine[Any, Any, T]
CoroT = TypeVar("CoroT", bound=Callable[..., Coro[Any]])

_LOGGER = logging.getLogger(__name__)


class NiceGOApi:
    """A class to interact with the Nice G.O. API.

    This class provides methods to authenticate, connect to the WebSocket API,
    and interact with barriers.

    Attributes:
        id_token (str | None): The ID token.

    Functions:
        event: Decorator to add an event listener.
        authenticate_refresh: Authenticate using a refresh token.
        authenticate: Authenticate using username and password.
        connect: Connect to the WebSocket API.
        subscribe: Subscribe to a receiver.
        unsubscribe: Unsubscribe from a receiver.
        close: Close the connection.
        get_all_barriers: Get all barriers.
    """

    def __init__(self) -> None:
        """Initialize the NiceGOApi object."""
        self.id_token: str | None = None
        self._closing_task: asyncio.Task[None] | None = None
        self._ws: WebSocketClient | None = None
        self._endpoints: dict[str, Any] | None = None
        self._session: aiohttp.ClientSession | None = None
        self._event_tasks: set[asyncio.Task[None]] = set()

        self._authenticator = AwsCognitoAuthenticator(
            REGION_NAME,
            CLIENT_ID,
            POOL_ID,
            IDENTITY_POOL_ID,
        )

    def event(self, coro: CoroT) -> CoroT:
        """Decorator to add an event listener.

        Info:
            This can only decorate coroutine functions.

        Args:
            coro (CoroT): The coroutine function to decorate.

        Examples:
            You can use this decorator to add event listeners to the API object.
            Some events include but are not limited to:

            - `connection_lost`: Triggered when the connection to the WebSocket API is
                lost.
            - `connected`: Triggered when the connection to the WebSocket API is
                established.
            - `data`: Triggered when data is received from an active subscription.
                See `subscribe`.

            >>> @api.event
            ... async def on_data(
            ...     data: dict[str, Any] | None = None,
            ... ) -> None:
            ...     if data is not None:
            ...         print(data)
        """
        if not asyncio.iscoroutinefunction(coro):
            msg = "The decorated function must be a coroutine"
            raise TypeError(msg)

        _LOGGER.debug("Adding event listener %s", coro.__name__)

        setattr(self, coro.__name__, coro)
        return coro

    async def _run_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Run an event coroutine. For internal use only.

        Args:
            coro (Callable[..., Coroutine[Any, Any, Any]]): The coroutine to run.
            event_name (str): The name of the event.
            data (dict[str, Any] | None): The data to pass to the event coroutine.
        """
        kwargs = {}
        if data is not None:
            kwargs["data"] = data
        try:
            await coro(**kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            _LOGGER.exception("Error while handling event %s", event_name)

    def _schedule_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        data: dict[str, Any] | None,
    ) -> None:
        """Schedule an event to be dispatched. For internal use only.

        Args:
            coro (Callable[..., Coroutine[Any, Any, Any]]): The coroutine to schedule.
            event_name (str): The name of the event.
            data (dict[str, Any] | None): The data to pass to the event coroutine.
        """
        wrapped = self._run_event(coro, event_name, data)
        task = asyncio.create_task(wrapped, name=f"NiceGO: {event_name}")
        self._event_tasks.add(task)  # See RUF006
        task.add_done_callback(self._event_tasks.discard)

    def _dispatch(self, event: str, data: dict[str, Any] | None = None) -> None:
        """Dispatch an event to listeners. For internal use only.

        Args:
            event (str): The name of the event.
            data (dict[str, Any] | None): The data to pass to the event coroutine.
        """
        method = f"on_{event}"

        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            _LOGGER.debug("Dispatching event %s", event)
            self._schedule_event(coro, method, data)

    async def authenticate_refresh(
        self,
        refresh_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Authenticate using a previous obtained refresh token.

        Args:
            refresh_token (str): The refresh token.
            session (aiohttp.ClientSession): The client session to use.

        Raises:
            AuthFailedError: If the authentication fails.
            ApiError: If an API error occurs.
        """
        self._session = session
        await self.__authenticate(None, None, refresh_token)

    async def authenticate(
        self,
        user_name: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> str | None:
        """Authenticate using username and password.

        Args:
            user_name (str): The username.
            password (str): The password.
            session (aiohttp.ClientSession): The client session to use.

        Returns:
            The refresh token.

        Raises:
            AuthFailedError: If the authentication fails.
            ApiError: If an API error occurs.
        """
        self._session = session
        return await self.__authenticate(user_name, password, None)

    async def __authenticate(
        self,
        user_name: str | None,
        password: str | None,
        refresh_token: str | None,
    ) -> str | None:
        """Authenticate using username and password or refresh token.

        Args:
            user_name (str | None): The username.
            password (str | None): The password.
            refresh_token (str | None): The refresh token.

        Returns:
            The refresh token.

        Raises:
            AuthFailedError: If the authentication fails.
            ApiError: If an API error occurs.
        """
        try:
            _LOGGER.debug("Authenticating")
            if user_name and password:
                token = await asyncio.to_thread(
                    self._authenticator.get_new_token,
                    user_name,
                    password,
                )
            elif refresh_token:
                token = await asyncio.to_thread(
                    self._authenticator.refresh_token,
                    refresh_token,
                )

            _LOGGER.debug("Authenticated")

            self.id_token = token.id_token

            if self._session is None:
                msg = "ClientSession not provided"
                raise ValueError(msg)

            # Get the endpoints while we're at it
            data = await self._session.get(ENDPOINTS_URL)
            endpoints = await data.json()
            self._endpoints = endpoints["endpoints"]
        except botocore.exceptions.ClientError as e:
            _LOGGER.exception("Exception while authenticating")
            if e.response["Error"]["Code"] == "NotAuthorizedException":
                raise AuthFailedError from e
            raise ApiError from e
        else:
            return token.refresh_token

    @property
    def closed(self) -> bool:
        """Check if the connection is closed."""
        return self._closing_task is not None

    async def connect(self, *, reconnect: bool = True) -> None:
        """Connect to the WebSocket API.

        Warning:
            No events will be dispatched until you subscribe to a receiver.
            Typically, you should pass the `organization` attribute of a barrier
            object to the `subscribe` method to start receiving data. Don't ask me
            why `organization` specifically, I don't know either.

        Danger:
            This method will block the event loop until the connection is closed.
            If you want to run this method in the background, you should run it in a
            separate thread or process.

        Args:
            reconnect (bool): Whether to reconnect if the connection is lost.

        Raises:
            NoAuthError: If the ID token is not available.
            ApiError: If an API error occurs.
            WebSocketError: If an error occurs while connecting.
        """
        backoff = ExponentialBackoff()
        try:
            while not self.closed:
                if self.id_token is None:
                    raise NoAuthError

                if self._endpoints is None:
                    msg = "Endpoints not available"
                    raise ApiError(msg)

                if self._session is None:
                    msg = "ClientSession not provided"
                    raise ValueError(msg)

                api_url = self._endpoints["GraphQL"]["device"]["wss"]

                _LOGGER.debug("Connecting to WebSocket API %s", api_url)

                self._ws = WebSocketClient()
                await self._ws.connect(
                    self._session,
                    self.id_token,
                    yarl.URL(api_url),
                    self._dispatch,
                    yarl.URL(self._endpoints["GraphQL"]["device"]["https"]).host,
                )

                _LOGGER.debug("Connected to WebSocket API")

                while True:
                    await self._ws.poll()
        except (
            OSError,
            WebSocketError,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as e:
            self._dispatch("connection_lost", {"exception": e})
            if not reconnect:
                _LOGGER.debug("Connection lost, not reconnecting")
                await self.close()
                raise

            if self.closed:
                return

            retry = backoff.delay()
            _LOGGER.debug("Connection lost, retrying in %s seconds", retry)
            await asyncio.sleep(retry)

    async def subscribe(self, receiver: str) -> str:
        """Subscribe to a receiver.

        Args:
            receiver (str): The receiver to subscribe to.

        Returns:
            The subscription ID. You can pass this into the `unsubscribe` method to
                unsubscribe from the receiver.

        Raises:
            WebSocketError: If no WebSocket connection is available.
        """
        if self._ws is None:
            msg = "No WebSocket connection"
            raise WebSocketError(msg)

        _LOGGER.debug("Subscribing to receiver %s", receiver)

        return await self._ws.subscribe(receiver)

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a receiver.

        Args:
            subscription_id (str): The subscription ID to unsubscribe from.

        Raises:
            WebSocketError: If no WebSocket connection is available
        """
        if self._ws is None:
            msg = "No WebSocket connection"
            raise WebSocketError(msg)

        _LOGGER.debug("Unsubscribing from subscription %s", subscription_id)

        await self._ws.unsubscribe(subscription_id)

    async def close(self) -> None:
        """Close the connection.

        Raises:
            NoAuthError: If the ID token is not available.
        """

        async def _close() -> None:
            if self._ws:
                await self._ws.close()

        _LOGGER.debug("Closing connection")

        self._closing_task = asyncio.create_task(_close())
        await self._closing_task

    async def get_all_barriers(self) -> list[Barrier]:
        """Get all barriers.

        Returns:
            A list of all barriers.

        Raises:
            NoAuthError: If the ID token is not available.
            ValueError: If the ClientSession or Endpoints are not available.
            ApiError: If an API error occurs.
        """
        if self.id_token is None:
            raise NoAuthError
        if self._session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self._endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self._endpoints["GraphQL"]["device"]["https"]

        _LOGGER.debug("Getting all barriers")
        _LOGGER.debug("API URL: %s", api_url)

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self._session.post(
            api_url,
            headers=headers,
            json=await get_request_template("get_all_barriers", None),
        )
        data = await response.json()

        _LOGGER.debug("Got all barriers")
        _LOGGER.debug("Data: %s", data)

        barriers = []

        for device in data["data"]["devicesListAll"]["devices"]:
            if device["state"]["connectionState"] is not None:
                connection_state = ConnectionState(
                    device["state"]["connectionState"]["connected"],
                    device["state"]["connectionState"]["updatedTimestamp"],
                )
            else:
                connection_state = None
            barrier_state = BarrierState(
                device["state"]["deviceId"],
                json.loads(device["state"]["desired"]),
                json.loads(device["state"]["reported"]),
                device["state"]["timestamp"],
                device["state"]["version"],
                connection_state,
            )
            barrier = Barrier(
                device["id"],
                device["type"],
                device["controlLevel"],
                device["attr"],
                barrier_state,
                self,
            )
            barriers.append(barrier)

        return barriers

    async def open_barrier(self, barrier_id: str) -> bool:
        """Open a barrier.

        Args:
            barrier_id (str): The ID of the barrier to open.

        Returns:
            Whether the barrier was opened successfully.

        Raises:
            NoAuthError: If the ID token is not available.
            ValueError: If the ClientSession or Endpoints are not available.
            ApiError: If an API error occurs.
        """
        if self.id_token is None:
            raise NoAuthError
        if self._session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self._endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self._endpoints["GraphQL"]["device"]["https"]

        _LOGGER.debug("Opening barrier %s", barrier_id)
        _LOGGER.debug("API URL: %s", api_url)

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self._session.post(
            api_url,
            headers=headers,
            json=await get_request_template("open_barrier", {"barrier_id": barrier_id}),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result

    async def close_barrier(self, barrier_id: str) -> bool:
        """Close a barrier.

        Args:
            barrier_id (str): The ID of the barrier to close.

        Returns:
            Whether the barrier was closed successfully."""
        if self.id_token is None:
            raise NoAuthError
        if self._session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self._endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self._endpoints["GraphQL"]["device"]["https"]

        _LOGGER.debug("Closing barrier %s", barrier_id)
        _LOGGER.debug("API URL: %s", api_url)

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self._session.post(
            api_url,
            headers=headers,
            json=await get_request_template(
                "close_barrier",
                {"barrier_id": barrier_id},
            ),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result

    async def light_on(self, barrier_id: str) -> bool:
        """Turn the light on.

        Args:
            barrier_id (str): The ID of the barrier to turn the light on.

        Returns:
            Whether the light was turned on successfully.

        Raises:
            NoAuthError: If the ID token is not available.
            ValueError: If the ClientSession or Endpoints are not available.
            ApiError: If an API error occurs.
        """
        if self.id_token is None:
            raise NoAuthError
        if self._session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self._endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self._endpoints["GraphQL"]["device"]["https"]

        _LOGGER.debug("Turning light on for barrier %s", barrier_id)
        _LOGGER.debug("API URL: %s", api_url)

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self._session.post(
            api_url,
            headers=headers,
            json=await get_request_template("light_on", {"barrier_id": barrier_id}),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result

    async def light_off(self, barrier_id: str) -> bool:
        """Turn the light off.

        Args:
            barrier_id (str): The ID of the barrier to turn the light off.

        Returns:
            Whether the light was turned off successfully.

        Raises:
            NoAuthError: If the ID token is not available.
            ValueError: If the ClientSession or Endpoints are not available.
            ApiError: If an API error occurs.
        """
        if self.id_token is None:
            raise NoAuthError
        if self._session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self._endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self._endpoints["GraphQL"]["device"]["https"]

        _LOGGER.debug("Turning light off for barrier %s", barrier_id)
        _LOGGER.debug("API URL: %s", api_url)

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self._session.post(
            api_url,
            headers=headers,
            json=await get_request_template("light_off", {"barrier_id": barrier_id}),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result
