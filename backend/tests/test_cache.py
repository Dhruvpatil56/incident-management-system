import json
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

import pytest

from incident_pipeline.cache.hotcache import Cache
from incident_pipeline.models import Incident, RcaCategory


class TestCache:
    """Tests for the read-through / write-through cache."""

    @pytest.fixture
    def redis(self):
        import fakeredis

        return fakeredis.FakeRedis()

    @pytest.fixture
    def cache(self, redis):
        return Cache(redis, default_ttl=300, stampede_beta=4.0)

    def make_incident(self) -> Incident:
        return Incident(
            title="Test incident",
            description="Something broke",
            source="test",
            root_cause="Deploy of v2.3.1 introduced regression in payment handler",
            rca_category=RcaCategory.code_deploy,
            rca_description="Rolled back, fixed, redeployed",
        )

    def test_cache_miss_calls_compute_fn(self, cache):
        incident = self.make_incident()
        compute = MagicMock(return_value=incident)

        result = cache.get_incident(incident.id, compute)
        assert result is not None
        assert result.id == incident.id
        assert result.title == incident.title
        compute.assert_called_once()

    def test_cache_hit_returns_cached(self, cache):
        incident = self.make_incident()
        cache.set_incident(incident)

        compute = MagicMock(return_value=incident)
        result = cache.get_incident(incident.id, compute)
        assert result is not None
        assert result.id == incident.id
        compute.assert_not_called()

    def test_write_through_primes_cache(self, cache, redis):
        incident = self.make_incident()
        cache.set_incident(incident)

        key = f"incident:{incident.id}"
        raw = redis.get(key)
        assert raw is not None
        decoded = json.loads(raw)
        assert decoded["id"] == str(incident.id)

    def test_increment_rca_stats(self, cache, redis):
        cache.increment_rca_stats(RcaCategory.code_deploy)
        cache.increment_rca_stats(RcaCategory.code_deploy)

        key = f"rca_stats:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

        # Check by iterating hgetall since fakeredis supports it
        assert redis.hexists(key, "code_deploy")
        assert int(redis.hget(key, "code_deploy")) == 2

    def test_cache_unavailable_falls_through(self, cache):
        incident = self.make_incident()
        # Break the redis client
        cache.redis = MagicMock()
        cache.redis.get.side_effect = Exception("connection refused")

        compute = MagicMock(return_value=incident)
        result = cache.get_incident(incident.id, compute)
        assert result.id == incident.id
        compute.assert_called_once()
