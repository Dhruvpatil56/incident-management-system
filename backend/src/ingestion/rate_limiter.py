from __future__ import annotations

import asyncio
import time


class TokenBucket:
    def __init__(self, capacity: int, refill_per_second: float):
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = refill_per_second
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.updated_at = now

    async def acquire(self, amount: float = 1.0) -> bool:
        async with self._lock:
            self._refill()
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

    async def release(self, amount: float = 1.0) -> None:
        async with self._lock:
            self.tokens = min(self.capacity, self.tokens + amount)
