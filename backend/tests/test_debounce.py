import pytest

from incident_pipeline.debounce.deduper import Debouncer
from incident_pipeline.models import Incident


class TestDebounce:
    """Tests for the Redis-backed deduper."""

    @pytest.fixture
    def redis(self):
        import fakeredis

        return fakeredis.FakeRedis()

    @pytest.fixture
    def debouncer(self, redis):
        return Debouncer(redis, window_seconds=30)

    def make_incident(self, **overrides) -> Incident:
        fields = dict(
            title="API latency spike",
            description="p95 latency jumped to 5s",
            source="datadog",
            root_cause="Deploy of v2.3.1 introduced regression in payment handler",
            rca_category="code_deploy",
            rca_description="Rolled back to v2.3.0, added null check, deployed v2.3.2",
        )
        fields.update(overrides)
        return Incident(**fields)

    def test_first_seen_is_new(self, debouncer):
        incident = self.make_incident()
        is_new, reason = debouncer.check(incident)
        assert is_new is True
        assert reason == "first_seen"

    def test_duplicate_is_detected(self, debouncer):
        incident = self.make_incident()
        debouncer.check(incident)  # first
        is_new, reason = debouncer.check(incident)  # second
        assert is_new is False
        assert reason == "duplicate_dropped"

    def test_different_source_not_duplicate(self, debouncer):
        a = self.make_incident(source="datadog")
        b = self.make_incident(source="pagerduty")
        debouncer.check(a)
        is_new, _ = debouncer.check(b)
        assert is_new is True

    def test_different_content_not_duplicate(self, debouncer):
        a = self.make_incident(title="Outage A")
        b = self.make_incident(title="Outage B")
        debouncer.check(a)
        is_new, _ = debouncer.check(b)
        assert is_new is True

    def test_window_expiry(self, redis, debouncer):
        incident = self.make_incident()
        debouncer.check(incident)

        # Simulate TTL expiry by flushing
        redis.flushall()

        is_new, _ = debouncer.check(incident)
        assert is_new is True