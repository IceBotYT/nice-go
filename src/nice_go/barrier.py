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
    """Class representing the connection state of a barrier."""

    connected: bool
    updatedTimestamp: datetime  # noqa: N815


@dataclass
class BarrierState:
    """Class representing the state of a barrier."""

    deviceId: str  # noqa: N815
    desired: dict[str, Any]
    reported: dict[str, Any]
    timestamp: str
    version: str
    connectionState: ConnectionState | None  # noqa: N815


@dataclass
class Barrier:
    """Class representing a barrier."""

    id: str
    type: str
    controlLevel: str  # noqa: N815
    attr: list[dict[str, str]]
    state: BarrierState
    api: NiceGOApi

    async def open(self) -> bool:
        """Open the barrier."""
        return await self.api._open_barrier(self.id)

    async def close(self) -> bool:
        """Close the barrier."""
        return await self.api._close_barrier(self.id)

    async def light_on(self) -> bool:
        """Turn on the light of the barrier."""
        return await self.api._light_on(self.id)

    async def light_off(self) -> bool:
        """Turn off the light of the barrier."""
        return await self.api._light_off(self.id)

    async def get_attr(self, key: str) -> str:
        """Get the value of an attribute."""
        attr = next((attr for attr in self.attr if attr["key"] == key), None)
        if attr is None:
            msg = f"Attribute with key {key} not found."
            raise ValueError(msg)
        return attr["value"]
