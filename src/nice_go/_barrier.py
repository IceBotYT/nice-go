# sourcery skip: snake-case-variable-declarations
"""Module containing classes for barriers.

This module contains classes for barriers and their states. The Barrier class
provides methods to interact with the barrier, such as opening and closing it,
and turning the light on and off.

Classes:
    ConnectionState: Represents the connection state of a barrier.
    BarrierState: Represents the state of a barrier.
    Barrier: Represents a barrier.
"""

# ruff: noqa: SLF001

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # This is a forward reference to avoid circular imports
    from datetime import datetime

    from nice_go.nice_go_api import NiceGOApi


@dataclass
class ConnectionState:
    """Class representing the connection state of a barrier.

    Attributes:
        connected (bool): A boolean indicating whether the barrier is connected.
        updatedTimestamp (datetime): The timestamp of the last update.
    """

    connected: bool
    updatedTimestamp: datetime  # noqa: N815


@dataclass
class BarrierState:
    """Class representing the state of a barrier.

    Attributes:
        deviceId (str): The device ID of the barrier.
        desired (dict[str, Any]): The desired state of the barrier.
        reported (dict[str, Any]): The reported state of the barrier.
        timestamp (str): The timestamp of the last update.
        version (str): The version of the barrier.
        connectionState (ConnectionState | None): The connection state of the barrier.
    """

    deviceId: str  # noqa: N815
    desired: dict[str, Any]
    reported: dict[str, Any]
    timestamp: str
    version: str
    connectionState: ConnectionState | None  # noqa: N815


@dataclass
class Barrier:
    """Class representing a barrier.

    Attributes:
        id (str): The ID of the barrier.
        type (str): The type of the barrier.
        controlLevel (str): The control level of the barrier.
        attr (list[dict[str, str]]): A list of attributes of the barrier.
        state (BarrierState): The state of the barrier.
        api (NiceGOApi): The NiceGO API object.

    Methods:
        open: Open the barrier.
        close: Close the barrier.
        light_on: Turn on the light of the barrier.
        light_off: Turn off the light of the barrier.
        get_attr: Get the value of an attribute.
    """

    id: str
    type: str
    controlLevel: str  # noqa: N815
    attr: list[dict[str, str]]
    state: BarrierState
    api: NiceGOApi

    async def open(self) -> bool:
        """Open the barrier.

        Returns:
            A boolean indicating whether the command was successful.
        """
        return await self.api.open_barrier(self.id)

    async def close(self) -> bool:
        """Close the barrier.

        Returns:
            A boolean indicating whether the command was successful.
        """
        return await self.api.close_barrier(self.id)

    async def light_on(self) -> bool:
        """Turn on the light of the barrier.

        Returns:
            A boolean indicating whether the command was successful.
        """
        return await self.api.light_on(self.id)

    async def light_off(self) -> bool:
        """Turn off the light of the barrier.

        Returns:
            A boolean indicating whether the command was successful.
        """
        return await self.api.light_off(self.id)

    async def get_attr(self, key: str) -> str:
        """Get the value of an attribute.

        Args:
            key (str): The key of the attribute.

        Returns:
            The value of the attribute.

        Raises:
            KeyError: If the attribute with the given key is not found.
        """
        attr = next((attr for attr in self.attr if attr["key"] == key), None)
        if attr is None:
            msg = f"Attribute with key {key} not found."
            raise KeyError(msg)
        return attr["value"]

    async def vacation_mode_on(self) -> None:
        """Turn on vacation mode for the barrier."""
        await self.api.vacation_mode_on(self.id)

    async def vacation_mode_off(self) -> None:
        """Turn off vacation mode for the barrier."""
        await self.api.vacation_mode_off(self.id)
