# ruff: noqa: SLF001

from unittest.mock import patch

from nice_go._backoff import ExponentialBackoff


async def test_backoff_reset() -> None:
    backoff = ExponentialBackoff(base=1)

    backoff._exp = 10
    backoff._last_invocation = 0

    with patch("nice_go._backoff.time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = 2049

        backoff.delay()

    assert backoff._exp == 1
