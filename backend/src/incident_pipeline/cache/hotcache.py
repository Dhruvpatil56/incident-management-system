from __future__ import annotations

import json
import logging
import random
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from incident_pipeline.config import settings
from incident_pipeline.models import Incident, RcaCategory

logger = logging.getLogger(__name__)


class Cache:
    """Read-through / write-through cache with probabilistic early expiration.

    Uses the XFetch algorithm to prevent cache stampedes: instead of all
    concurrent requests hitting the DB when a key expires, only ~1/beta of
    them recompute while the rest get the stale value.
    """

    def __init__(
        self,
        redis_client,
        default_ttl: int = settings.cache_default_ttl,
        stampede_beta: float = settings.cache_stampede_beta,
    ):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.beta = stampede_beta

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def get_incident(
        self, incident_id: UUID, compute_fn: Callable[[], Incident | None]
    ) -> Incident | None:
        """Read-through: returns cached incident or fetches via compute_fn."""
        key = f"incident:{incident_id}"
        def _wrap() -> dict | None:
            incident = compute_fn()
            if incident is None:
                return None
            return incident.model_dump(mode="json")

        cached = self._get_with_stampede_protection(
            key,
            _wrap,
            self.default_ttl,
        )
        if isinstance(cached, dict):
            return Incident(**cached)
        return cached

    def get_recent_incidents(
        self, compute_fn: Callable[[], list[Incident]], limit: int = 50
    ) -> list[Incident]:
        """Read-through for the recent-incidents list (short TTL)."""
        key = "incidents:recent"
        cached = self._get_with_stampede_protection(
            key,
            lambda: [m.model_dump(mode="json") for m in compute_fn()],
            settings.cache_list_ttl,
        )
        if isinstance(cached, list):
            return [Incident(**item) for item in cached]
        return compute_fn()

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def set_incident(self, incident: Incident) -> None:
        """Write-through: prime the cache immediately after storing."""
        key = f"incident:{incident.id}"
        try:
            self.redis.setex(
                key,
                self.default_ttl,
                incident.model_dump_json(),
            )
        except Exception:
            logger.warning("failed to warm cache for incident %s", incident.id)

    def increment_rca_stats(self, category: RcaCategory) -> None:
        """Atomic increment of daily RCA category counter."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"rca_stats:{today}"
        try:
            self.redis.hincrby(key, category.value, 1)
            self.redis.expire(key, settings.cache_rca_stats_ttl)
        except Exception:
            logger.warning("failed to update rca_stats for %s", category)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_with_stampede_protection(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: int,
    ) -> Any:
        try:
            cached = self.redis.get(key)
        except Exception:
            logger.warning("cache unavailable for key %s, falling through", key)
            cached = None

        if cached is not None:
            try:
                remaining = self.redis.ttl(key)
            except Exception:
                remaining = ttl

            # XFetch: probabilistically decide whether to refresh early
            if 0 < remaining < ttl * 0.5:
                prob = (1.0 - remaining / (ttl * 0.5)) ** self.beta
                if random.random() < prob:
                    cached = None

        if cached is None:
            value = compute_fn()
            if value is not None:
                jitter = ttl + random.randint(-ttl // 10, ttl // 10)
                try:
                    self.redis.setex(key, max(jitter, 10), json.dumps(value) if not isinstance(value, str) else value)
                except Exception:
                    pass
            return value

        if isinstance(cached, bytes):
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return cached
        return cached