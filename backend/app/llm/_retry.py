"""Retry helpers for external HTTP / SDK calls.

We implement a small async retry runner instead of using tenacity's decorator
directly because we need to surface the attempt count back to the caller (so
`JudgeResult.retry_count` and `NormalizedMolecule` notes can reflect it).
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")


_RETRYABLE_NAMES: frozenset[str] = frozenset(
    {
        # OpenAI SDK
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "APIStatusError",
        # Anthropic SDK
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
        # Google generativeai / google.api_core
        "ResourceExhausted",
        "DeadlineExceeded",
        "ServiceUnavailable",
        "InternalServerError",
        "RetryError",
    }
)


def is_retryable_exception(exc: BaseException) -> bool:
    """Retry on network errors, timeouts, 429, and 5xx — never on auth errors."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPError):
        return True
    code = getattr(exc, "status_code", None)
    if code is None:
        # Anthropic exposes response.status_code; openai's APIStatusError has .status_code too
        resp = getattr(exc, "response", None)
        if resp is not None:
            code = getattr(resp, "status_code", None)
    if isinstance(code, int):
        if code == 429:
            return True
        if 500 <= code < 600:
            return True
        # 4xx (auth, bad request) — do NOT retry
        return False
    return exc.__class__.__name__ in _RETRYABLE_NAMES


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    jitter: float = 0.25,
) -> tuple[T, int]:
    """Run `fn` up to max_attempts times with exponential backoff + jitter.

    Returns (result, retry_count) where retry_count is the number of retries
    that happened before success (0 on first-try success).

    Reraises the last exception when all attempts are exhausted, or immediately
    when the exception is not retryable.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            result = await fn()
            return result, attempt
        except BaseException as exc:  # noqa: BLE001
            last_exc = exc
            if not is_retryable_exception(exc):
                raise
            if attempt == max_attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2**attempt))
            spread = delay * jitter
            delay = max(0.0, delay + random.uniform(-spread, spread))
            await asyncio.sleep(delay)
    assert last_exc is not None  # unreachable
    raise last_exc
