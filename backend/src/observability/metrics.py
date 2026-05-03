from __future__ import annotations

import asyncio
import contextlib
import logging
import time

logger = logging.getLogger(__name__)


class ThroughputCounter:
    def __init__(self):
        self._count = 0
        self._last_at = time.monotonic()
        self._task: asyncio.Task | None = None

    def increment(self) -> None:
        self._count += 1

    async def start(self) -> None:
        async def _loop() -> None:
            while True:
                await asyncio.sleep(5)
                now = time.monotonic()
                delta = max(now - self._last_at, 1e-6)
                logger.info("Signals/sec: %.2f", self._count / delta)
                self._count = 0
                self._last_at = now

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
