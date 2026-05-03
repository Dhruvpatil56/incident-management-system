from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from observability.prometheus import db_retry_attempts_total

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.05,
    db: str = "postgres",
    operation: str = "unknown",
) -> T:
    """Retry transient DB operations with exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - exercised via callers
            last_error = exc
            if attempt == attempts - 1:
                break
            db_retry_attempts_total.labels(db=db, operation=operation).inc()
            time.sleep(base_delay_seconds * (2**attempt))
    assert last_error is not None
    raise last_error
