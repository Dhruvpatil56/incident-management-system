from __future__ import annotations

import json

from observability.prometheus import nats_publish_failures_total, nats_publish_total, queue_lag_estimate
from signals.models import Signal


class SignalProducer:
    def __init__(self, nats_client, subject: str):
        self.nats = nats_client
        self.subject = subject

    async def publish(self, signal: Signal) -> None:
        try:
            await self.nats.publish(
                self.subject,
                json.dumps(signal.model_dump(mode="json")).encode(),
            )
            nats_publish_total.inc()
            # Placeholder until broker lag metrics are wired from NATS monitoring APIs.
            queue_lag_estimate.set(0)
        except Exception:
            nats_publish_failures_total.inc()
            raise
