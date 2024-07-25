# ruff: noqa: SLF001

from nice_go._backoff import ExponentialBackoff


async def test_backoff_reset() -> None:
    backoff = ExponentialBackoff(base=1)

    backoff._exp = 10
    backoff._last_invocation = 0

    backoff.delay()

    assert backoff._exp == 1
