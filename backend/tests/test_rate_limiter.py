import asyncio

import pytest

from ingestion.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_burst_capacity():
    bucket = TokenBucket(capacity=3, refill_per_second=1)
    assert await bucket.acquire()
    assert await bucket.acquire()
    assert await bucket.acquire()


@pytest.mark.asyncio
async def test_exhaustion_then_refill():
    bucket = TokenBucket(capacity=1, refill_per_second=10)
    assert await bucket.acquire()
    assert not await bucket.acquire()
    await asyncio.sleep(0.2)
    assert await bucket.acquire()
