from __future__ import annotations

import logging
from collections.abc import Callable

from incident_pipeline.cache.hotcache import Cache
from incident_pipeline.debounce.deduper import Debouncer
from incident_pipeline.models import Incident, IncidentResult
from incident_pipeline.rca.policy import RcaPolicy
from observability.prometheus import debounce_dropped_total, incident_created_total

logger = logging.getLogger(__name__)

StoreFn = Callable[[Incident], Incident]


class IncidentPipeline:
    """Synchronous incident processing pipeline.

    Order: Debounce → RCA → Store + Cache
    """

    def __init__(
        self,
        debouncer: Debouncer,
        rca_policy: RcaPolicy,
        cache: Cache,
        store_fn: StoreFn,
    ):
        self.debouncer = debouncer
        self.rca = rca_policy
        self.cache = cache
        self.store = store_fn

    def process(self, incident: Incident) -> IncidentResult:
        # 1. Debounce — cheapest check first
        is_new, reason = self.debouncer.check(incident)
        if not is_new:
            debounce_dropped_total.inc()
            return IncidentResult(
                status=204, action="dropped", reason=reason
            )

        # 2. RCA enforcement — semantic validation
        errors = self.rca.validate(
            incident.root_cause, incident.rca_description
        )
        if errors:
            return IncidentResult(
                status=422, action="rejected", errors=errors
            )

        # 3. Store + write-through cache
        record = self.store(incident)
        self.cache.set_incident(record)
        self.cache.increment_rca_stats(record.rca_category)

        logger.info(
            "incident %s created (source=%s, category=%s)",
            record.id,
            record.source,
            record.rca_category,
        )
        incident_created_total.inc()
        return IncidentResult(
            status=201, action="created", incident=record
        )


class AsyncIncidentWorker:
    """Async ingestion path for webhooks/queues.

    On validation failure the message goes to a dead-letter queue
    instead of being silently dropped.
    """

    def __init__(
        self,
        pipeline: IncidentPipeline,
        dead_letter_fn: Callable[[Incident, list[str]], None] | None = None,
    ):
        self.pipeline = pipeline
        self.dead_letter = dead_letter_fn

    def handle(self, incident: Incident) -> None:
        result = self.pipeline.process(incident)
        if result.status == 422 and self.dead_letter is not None:
            self.dead_letter(incident, result.errors or [])
