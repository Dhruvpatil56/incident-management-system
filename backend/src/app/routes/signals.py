from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_rate_limiter, get_signal_producer, get_signal_store
from ingestion.producer import SignalProducer
from ingestion.rate_limiter import TokenBucket
from observability.prometheus import queue_inflight_signals, signals_ingested_total, signals_rejected_total
from signals.models import Signal
from signals.store import InMemorySignalStore

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_signal(
    request: Request,
    signal: Signal,
    rate_limiter: TokenBucket = Depends(get_rate_limiter),
    signal_store: InMemorySignalStore = Depends(get_signal_store),
    producer: SignalProducer = Depends(get_signal_producer),
) -> dict:
    if not await rate_limiter.acquire():
        signals_rejected_total.labels(reason="rate_limit").inc()
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    semaphore = getattr(request.app.state, "ingest_semaphore", None)
    if semaphore is not None:
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=0.01)
            queue_inflight_signals.inc()
        except TimeoutError:
            signals_rejected_total.labels(reason="backpressure").inc()
            raise HTTPException(status_code=503, detail="ingestion backpressure")
    try:
        await signal_store.insert(signal)
        await producer.publish(signal)
        signals_ingested_total.inc()
    finally:
        if semaphore is not None:
            queue_inflight_signals.dec()
            semaphore.release()
    throughput = getattr(request.app.state, "throughput", None)
    if throughput is not None:
        throughput.increment()
    return {"accepted": True, "signal_id": str(signal.id)}
