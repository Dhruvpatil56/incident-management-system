from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from observability.prometheus import db_retry_attempts_total

T = TypeVar("T")


async def with_async_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.05,
    db: str = "mongo",
    operation: str = "unknown",
) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await fn()
        except Exception as exc:  # pragma: no cover - exercised via callers
            last_error = exc
            if attempt == attempts - 1:
                break
            db_retry_attempts_total.labels(db=db, operation=operation).inc()
            await asyncio.sleep(base_delay_seconds * (2**attempt))
    assert last_error is not None
    raise last_error
