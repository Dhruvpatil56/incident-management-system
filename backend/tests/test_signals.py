import pytest

from incident_pipeline.models import Severity
from signals.models import Signal
from signals.store import InMemorySignalStore


@pytest.mark.asyncio
async def test_signal_store_roundtrip():
    store = InMemorySignalStore()
    signal = Signal(
        component_id="db-1",
        component_type="rdbms",
        severity=Severity.p0,
        raw_payload={"cpu": 99},
    )
    await store.insert(signal)
    found = await store.find_by_component("db-1")
    assert len(found) == 1
    assert found[0].raw_payload["cpu"] == 99
