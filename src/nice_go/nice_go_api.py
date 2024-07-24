"""Parses data from the Nice G.O. API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, TypeVar

import aiohttp
import botocore
import yarl

from nice_go.aws_cognito_authenticator import AwsCognitoAuthenticator
from nice_go.backoff import ExponentialBackoff
from nice_go.barrier import Barrier, BarrierState, ConnectionState
from nice_go.const import (
    CLIENT_ID,
    ENDPOINTS_URL,
    IDENTITY_POOL_ID,
    POOL_ID,
    REGION_NAME,
)
from nice_go.exceptions import (
    ApiError,
    AuthFailedError,
    NoAuthError,
    WebSocketError,
)
from nice_go.util import get_request_template
from nice_go.ws_client import WebSocketClient

T = TypeVar("T")
Coro = Coroutine[Any, Any, T]
CoroT = TypeVar("CoroT", bound=Callable[..., Coro[Any]])

_LOGGER = logging.getLogger(__name__)


class NiceGOApi:
    def __init__(self) -> None:
        self.id_token: str | None = None
        self._closing_task: asyncio.Task[None] | None = None
        self.ws: WebSocketClient | None = None
        self.endpoints: dict[str, Any] | None = None
        self.session: aiohttp.ClientSession | None = None
        self._event_tasks: set[asyncio.Task[None]] = set()

        self.authenticator = AwsCognitoAuthenticator(
            REGION_NAME,
            CLIENT_ID,
            POOL_ID,
            IDENTITY_POOL_ID,
        )

    def event(self, coro: CoroT) -> CoroT:
        """Decorator to add an event listener."""
        if not asyncio.iscoroutinefunction(coro):
            msg = "The decorated function must be a coroutine"
            raise TypeError(msg)

        setattr(self, coro.__name__, coro)
        return coro

    async def _run_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> None:
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
        """Schedule an event to be dispatched."""
        wrapped = self._run_event(coro, event_name, data)
        task = asyncio.create_task(wrapped, name=f"NiceGO: {event_name}")
        self._event_tasks.add(task)  # See RUF006
        task.add_done_callback(self._event_tasks.discard)

    def dispatch(self, event: str, data: dict[str, Any] | None = None) -> None:
        """Dispatch an event to the listeners."""
        method = "on_" + event

        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, method, data)

    async def authenticate_refresh(
        self,
        refresh_token: str,
        session: aiohttp.ClientSession,
    ) -> str | None:
        """Authenticate using a previous obtained refresh token."""
        self.session = session
        return await self.__authenticate(None, None, refresh_token)

    async def authenticate(
        self,
        user_name: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> str | None:
        """Authenticate using username and password."""
        self.session = session
        return await self.__authenticate(user_name, password, None)

    async def __authenticate(
        self,
        user_name: str | None,
        password: str | None,
        refresh_token: str | None,
    ) -> str | None:
        try:
            if refresh_token is None:
                if user_name is None or password is None:
                    msg = "Username and password must be provided"
                    raise ValueError(msg)
                token = await asyncio.to_thread(
                    self.authenticator.get_new_token,
                    user_name,
                    password,
                )
            else:
                token = await asyncio.to_thread(
                    self.authenticator.refresh_token,
                    refresh_token,
                )

            self.id_token = token.id_token

            if self.session is None:
                msg = "ClientSession not provided"
                raise ValueError(msg)

            # Get the endpoints while we're at it
            data = await self.session.get(ENDPOINTS_URL)
            endpoints = await data.json()
            self.endpoints = endpoints["endpoints"]
        except botocore.exceptions.ClientError as e:
            _LOGGER.exception("Exception while authenticating")
            if e.response["Error"]["Code"] == "NotAuthorizedException":
                raise AuthFailedError from e
            raise ApiError from e
        else:
            return token.refresh_token

    @property
    def closed(self) -> bool:
        return self._closing_task is not None

    async def connect(self, *, reconnect: bool = True) -> None:
        backoff = ExponentialBackoff()
        try:
            while not self.closed:
                if self.id_token is None:
                    raise NoAuthError

                if self.endpoints is None:
                    msg = "Endpoints not available"
                    raise ApiError(msg)

                if self.session is None:
                    msg = "ClientSession not provided"
                    raise ValueError(msg)

                api_url = self.endpoints["GraphQL"]["device"]["wss"]

                self.ws = WebSocketClient()
                await self.ws.connect(
                    self.session,
                    self.id_token,
                    yarl.URL(api_url),
                    self.dispatch,
                    yarl.URL(self.endpoints["GraphQL"]["device"]["https"]).host,
                )

                while True:
                    await self.ws.poll()
        except (
            OSError,
            WebSocketError,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as e:
            self.dispatch("connection_lost", {"exception": e})
            if not reconnect:
                await self.close()
                raise

            if self.closed:
                return

            retry = backoff.delay()
            _LOGGER.exception("Connection lost, retrying in %s seconds", retry)
            await asyncio.sleep(retry)

    async def subscribe(self, receiver: str) -> str:
        if self.ws is None:
            msg = "No WebSocket connection"
            raise WebSocketError(msg)

        return await self.ws.subscribe(receiver)

    async def unsubscribe(self, receiver: str) -> None:
        if self.ws is None:
            msg = "No WebSocket connection"
            raise WebSocketError(msg)

        await self.ws.unsubscribe(receiver)

    async def close(self) -> None:
        async def _close() -> None:
            if self.ws:
                await self.ws.close()

        self._closing_task = asyncio.create_task(_close())
        await self._closing_task

    async def get_all_barriers(self) -> list[Barrier]:
        if self.id_token is None:
            raise NoAuthError
        if self.session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self.endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self.endpoints["GraphQL"]["device"]["https"]

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self.session.post(
            api_url,
            headers=headers,
            json=await get_request_template("get_all_barriers", None),
        )
        data = await response.json()

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

    async def _open_barrier(self, barrier_id: str) -> bool:
        if self.id_token is None:
            raise NoAuthError
        if self.session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self.endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self.endpoints["GraphQL"]["device"]["https"]

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self.session.post(
            api_url,
            headers=headers,
            json=await get_request_template("open_barrier", {"barrier_id": barrier_id}),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result

    async def _close_barrier(self, barrier_id: str) -> bool:
        if self.id_token is None:
            raise NoAuthError
        if self.session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self.endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self.endpoints["GraphQL"]["device"]["https"]

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self.session.post(
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

    async def _light_on(self, barrier_id: str) -> bool:
        if self.id_token is None:
            raise NoAuthError
        if self.session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self.endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self.endpoints["GraphQL"]["device"]["https"]

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self.session.post(
            api_url,
            headers=headers,
            json=await get_request_template("light_on", {"barrier_id": barrier_id}),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result

    async def _light_off(self, barrier_id: str) -> bool:
        if self.id_token is None:
            raise NoAuthError
        if self.session is None:
            msg = "ClientSession not provided"
            raise ValueError(msg)
        if self.endpoints is None:
            msg = "Endpoints not available"
            raise ApiError(msg)

        api_url = self.endpoints["GraphQL"]["device"]["https"]

        headers = {"Authorization": self.id_token, "Content-Type": "application/json"}

        response = await self.session.post(
            api_url,
            headers=headers,
            json=await get_request_template("light_off", {"barrier_id": barrier_id}),
        )
        data = await response.json()
        result: bool = data["data"]["devicesControl"]

        return result
