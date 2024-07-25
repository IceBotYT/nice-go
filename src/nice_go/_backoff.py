"""An implementation of the exponential backoff algorithm.

This module provides a class that implements the exponential backoff
algorithm.  This is useful for retrying transmissions in a distributed
network where collisions may occur. The algorithm increases the delay
between retries exponentially up to a maximum value.

Classes:
    ExponentialBackoff: An implementation of the exponential backoff algorithm.
"""

from __future__ import annotations

import random
import time
from typing import Callable

__all__ = ("ExponentialBackoff",)


class ExponentialBackoff:
    """An implementation of the exponential backoff algorithm

    Provides a convenient interface to implement an exponential backoff
    for reconnecting or retrying transmissions in a distributed network.

    Once instantiated, the delay method will return the next interval to
    wait for when retrying a connection or transmission.  The maximum
    delay increases exponentially with each retry up to a maximum of
    2^10 * base, and is reset if no more attempts are needed in a period
    of 2^11 * base seconds.

    Parameters:
        base:
            The base delay in seconds. The first retry-delay will be up to
            this many seconds.
        integral:
            Set to ``True`` if whole periods of base is desirable, otherwise any
            number in between may be returned.
    """

    def __init__(self, base: int = 1, *, integral: bool = False):
        """Initialize the ExponentialBackoff object."""
        self._base: int = base

        self._exp: int = 0
        self._max: int = 10
        self._reset_time: int = base * 2**11
        self._last_invocation: float = time.monotonic()

        # Use our own random instance to avoid messing with global one
        rand = random.Random()  # noqa: S311
        rand.seed()

        self._randfunc: Callable[[int, int], float] = (
            rand.randrange if integral else rand.uniform  # type: ignore[assignment]
        )

    def delay(self) -> float:
        """Compute the next delay

        Returns the next delay to wait according to the exponential
        backoff algorithm.  This is a value between 0 and base * 2^exp
        where exponent starts off at 1 and is incremented at every
        invocation of this method up to a maximum of 10.

        If a period of more than base * 2^11 has passed since the last
        retry, the exponent is reset to 1.

        Returns:
            The next delay to wait in seconds.
        """
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation

        if interval > self._reset_time:
            self._exp = 0

        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2**self._exp)
