import pytest

from incident_pipeline.cache.hotcache import Cache
from incident_pipeline.db.store import InMemoryStore
from incident_pipeline.debounce.deduper import Debouncer
from incident_pipeline.models import Incident, RcaCategory
from incident_pipeline.pipeline import IncidentPipeline
from incident_pipeline.rca.policy import RcaPolicy


class TestPipeline:
    """Integration tests for the full incident pipeline."""

    @pytest.fixture
    def redis(self):
        import fakeredis

        return fakeredis.FakeRedis()

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def pipeline(self, redis, store):
        return IncidentPipeline(
            debouncer=Debouncer(redis, window_seconds=30),
            rca_policy=RcaPolicy(min_length=10, max_length=500),
            cache=Cache(redis, default_ttl=300),
            store_fn=store.create,
        )

    def make_valid_incident(self, **overrides) -> Incident:
        fields = dict(
            title="API latency spike",
            description="p95 latency jumped to 5s at 14:32 UTC",
            source="datadog",
            root_cause="Deploy of v2.3.1 introduced regression in payment handler",
            rca_category=RcaCategory.code_deploy,
            rca_description="Rolled back to v2.3.0, added null check, deployed v2.3.2",
        )
        fields.update(overrides)
        return Incident(**fields)

    def test_happy_path(self, pipeline):
        incident = self.make_valid_incident()
        result = pipeline.process(incident)
        assert result.status == 201
        assert result.action == "created"
        assert result.incident is not None

    def test_duplicate_is_dropped(self, pipeline):
        incident = self.make_valid_incident()
        pipeline.process(incident)
        result = pipeline.process(incident)
        assert result.status == 204
        assert result.action == "dropped"
        assert result.reason == "duplicate_dropped"

    def test_missing_rca_is_rejected(self, pipeline):
        incident = self.make_valid_incident(root_cause="", rca_description="")
        result = pipeline.process(incident)
        assert result.status == 422
        assert result.action == "rejected"
        assert result.errors is not None
        assert len(result.errors) > 0

    def test_placeholder_rca_is_rejected(self, pipeline):
        incident = self.make_valid_incident(root_cause="TBD", rca_description="TBD")
        result = pipeline.process(incident)
        assert result.status == 422
        assert result.errors is not None

    def test_duplicate_after_different_source_is_accepted(self, pipeline):
        a = self.make_valid_incident(source="datadog")
        b = self.make_valid_incident(source="pagerduty")
        r1 = pipeline.process(a)
        r2 = pipeline.process(b)
        assert r1.status == 201
        assert r2.status == 201

    def test_duplicate_after_window_expiry(self, pipeline, redis):
        incident = self.make_valid_incident()
        pipeline.process(incident)
        redis.flushall()  # clear debounce keys
        result = pipeline.process(incident)
        assert result.status == 201  # accepted as new