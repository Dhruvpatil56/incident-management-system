import pytest

from alerting.router import AlertRouter
from incident_pipeline.models import Incident, RcaCategory, Severity


class _MockStrategy:
    def __init__(self):
        self.sent = False

    async def send(self, _incident):
        self.sent = True
        return True


@pytest.mark.asyncio
async def test_alert_router_dispatches_by_severity():
    incident = Incident(
        title="db down",
        description="outage",
        source="monitor",
        root_cause="known",
        rca_category=RcaCategory.unknown,
        rca_description="known",
        severity=Severity.p0,
    )
    strategy = _MockStrategy()
    router = AlertRouter({Severity.p0: [strategy]})
    result = await router.dispatch(incident)
    assert result == [True]
    assert strategy.sent
