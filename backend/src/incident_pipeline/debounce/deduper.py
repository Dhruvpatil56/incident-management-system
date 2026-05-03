from __future__ import annotations

import hashlib
import json

from incident_pipeline.config import settings
from incident_pipeline.models import Incident
from observability.prometheus import db_timing


def _debounce_key(incident: Incident, window_seconds: int) -> str:
    """Generate a deterministic dedup key from an incident.

    Normalizes fields (lowercase, stripped) and snaps the timestamp to
    a time bucket so near-simultaneous duplicates collide.
    """
    normalized = {
        "source": incident.source.strip().lower(),
        "title": incident.title.strip().lower(),
        "description": incident.description.strip().lower(),
        "time_bucket": int(incident.created_at.timestamp() / window_seconds),
    }
    raw = json.dumps(normalized, sort_keys=True).encode()
    h = hashlib.sha256(raw).hexdigest()
    return f"debounce:{normalized['source']}:{h[:16]}"


class Debouncer:
    """Prevents duplicate work items using Redis SET NX with TTL.

    Uses atomic SET NX EX to avoid TOCTOU races between concurrent
    workers (the classic SET + GET race). Lua scripting fallback is
    avoided to maintain compatibility with fakeredis in tests.
    """

    def __init__(
        self,
        redis_client,
        window_seconds: int = settings.debounce_window_seconds,
    ):
        self.redis = redis_client
        self.window = window_seconds

    def check(self, incident: Incident) -> tuple[bool, str]:
        """Returns (is_new, reason).

        'new' — first time this incident has been seen within the window.
        'duplicate' — an identical incident was already processed.
        """
        key = _debounce_key(incident, self.window)
        # SET NX EX is atomic in Redis — no TOCTOU race
        with db_timing("redis", "debounce_check"):
            result = self.redis.set(key, "1", nx=True, ex=self.window)
        if result:
            return True, "first_seen"
        return False, "duplicate_dropped"

    def is_seen(self, incident: Incident) -> bool:
        """Non-atomic informational check — no TOCTOU guarantees."""
        key = _debounce_key(incident, self.window)
        with db_timing("redis", "debounce_exists"):
            return bool(self.redis.exists(key))
