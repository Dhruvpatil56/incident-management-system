from incident_pipeline.models import Incident, IncidentState, RcaCategory
from workflow.rca_guard import RcaGuard
from workflow.state_machine import validate_transition


def _incident(**overrides) -> Incident:
    base = dict(
        title="t",
        description="d",
        source="s",
        root_cause="Deploy caused regression",
        rca_category=RcaCategory.code_deploy,
        rca_description="Rollback fixed issue",
        rca_verified_by="oncall",
    )
    base.update(overrides)
    return Incident(**base)


def test_valid_transition():
    assert validate_transition(IncidentState.open, IncidentState.investigating)


def test_invalid_transition():
    assert not validate_transition(IncidentState.open, IncidentState.closed)


def test_rca_guard_requires_fields():
    assert RcaGuard.can_close(_incident())
    assert not RcaGuard.can_close(_incident(rca_verified_by=None))
