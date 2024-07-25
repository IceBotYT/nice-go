from unittest.mock import AsyncMock, MagicMock

import pytest
from nice_go import Barrier
from nice_go._barrier import BarrierState


async def test_open() -> None:
    barrier = Barrier(
        "barrier_id",
        "barrier_type",
        "control_level",
        [],
        BarrierState(
            deviceId="device_id",
            desired={"key": "value"},
            reported={"key": "value"},
            timestamp="timestamp",
            version="version",
            connectionState=None,
        ),
        MagicMock(_open_barrier=AsyncMock(return_value=True)),
    )
    assert await barrier.open() is True


async def test_close() -> None:
    barrier = Barrier(
        "barrier_id",
        "barrier_type",
        "control_level",
        [],
        BarrierState(
            deviceId="device_id",
            desired={"key": "value"},
            reported={"key": "value"},
            timestamp="timestamp",
            version="version",
            connectionState=None,
        ),
        MagicMock(_close_barrier=AsyncMock(return_value=True)),
    )
    assert await barrier.close() is True


async def test_light_on() -> None:
    barrier = Barrier(
        "barrier_id",
        "barrier_type",
        "control_level",
        [],
        BarrierState(
            deviceId="device_id",
            desired={"key": "value"},
            reported={"key": "value"},
            timestamp="timestamp",
            version="version",
            connectionState=None,
        ),
        MagicMock(_light_on=AsyncMock(return_value=True)),
    )
    assert await barrier.light_on() is True


async def test_light_off() -> None:
    barrier = Barrier(
        "barrier_id",
        "barrier_type",
        "control_level",
        [],
        BarrierState(
            deviceId="device_id",
            desired={"key": "value"},
            reported={"key": "value"},
            timestamp="timestamp",
            version="version",
            connectionState=None,
        ),
        MagicMock(_light_off=AsyncMock(return_value=True)),
    )
    assert await barrier.light_off() is True


async def test_get_attr() -> None:
    barrier = Barrier(
        "barrier_id",
        "barrier_type",
        "control_level",
        [{"key": "key", "value": "value"}],
        BarrierState(
            deviceId="device_id",
            desired={"key": "value"},
            reported={"key": "value"},
            timestamp="timestamp",
            version="version",
            connectionState=None,
        ),
        MagicMock(),
    )
    assert await barrier.get_attr("key") == "value"


async def test_get_attr_not_found() -> None:
    barrier = Barrier(
        "barrier_id",
        "barrier_type",
        "control_level",
        [{"key": "key", "value": "value"}],
        BarrierState(
            deviceId="device_id",
            desired={"key": "value"},
            reported={"key": "value"},
            timestamp="timestamp",
            version="version",
            connectionState=None,
        ),
        MagicMock(),
    )
    with pytest.raises(KeyError) as exc_info:
        await barrier.get_attr("not_found")
    assert str(exc_info.value) == "'Attribute with key not_found not found.'"
