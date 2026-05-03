from __future__ import annotations

import json
from time import perf_counter

from incident_pipeline.models import Incident
from incident_pipeline.pipeline import IncidentPipeline
from observability.prometheus import consumer_messages_total, consumer_processing_duration_seconds
from signals.models import Signal
from signals.store import SignalStore


class SignalConsumer:
    def __init__(
        self,
        nats_client,
        subject: str,
        store: SignalStore,
        pipeline: IncidentPipeline,
        redis_client=None,
        link_window_seconds: int = 10,
    ):
        self.nats = nats_client
        self.subject = subject
        self.store = store
        self.pipeline = pipeline
        self.redis = redis_client
        self.window = link_window_seconds

    async def start(self) -> None:
        await self.nats.subscribe(self.subject, cb=self._handle)

    async def _handle(self, msg) -> None:
        started = perf_counter()
        payload = json.loads(msg.data.decode())
        signal = Signal(**payload)
        try:
            link_key = f"signal-link:{signal.component_id}"
            existing_id = self.redis.get(link_key) if self.redis is not None else None
            if existing_id:
                linked = signal.model_copy(update={"work_item_id": existing_id.decode()})
                await self.store.insert(linked)
                return
            incident = Incident(
                title=payload.get("title", f"Signal for {signal.component_id}"),
                description=payload.get("description", "Signal-driven incident"),
                source=payload.get("source", "signal"),
                root_cause=payload.get("root_cause", "Pending investigation"),
                rca_category=payload.get("rca_category", "unknown"),
                rca_description=payload.get("rca_description", "Pending RCA"),
                component=signal.component_type,
                severity=signal.severity,
                first_signal_at=signal.created_at,
            )
            result = self.pipeline.process(incident)
            if result.incident:
                linked_id = str(result.incident.id)
                linked = signal.model_copy(update={"work_item_id": linked_id})
                if self.redis is not None:
                    self.redis.setex(link_key, self.window, linked_id)
                await self.store.insert(linked)
                return
            await self.store.insert(signal)
        finally:
            consumer_messages_total.inc()
            consumer_processing_duration_seconds.observe(max(perf_counter() - started, 0.0))
