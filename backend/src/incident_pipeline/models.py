from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RcaCategory(str, Enum):
    code_deploy = "code_deploy"
    config_change = "config_change"
    dependency_failure = "dependency_failure"
    resource_exhaustion = "resource_exhaustion"
    human_error = "human_error"
    external_outage = "external_outage"
    security_incident = "security_incident"
    unknown = "unknown"


class IncidentState(str, Enum):
    open = "OPEN"
    investigating = "INVESTIGATING"
    resolved = "RESOLVED"
    closed = "CLOSED"


class Severity(str, Enum):
    p0 = "P0"
    p1 = "P1"
    p2 = "P2"
    p3 = "P3"


class Incident(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    source: str
    root_cause: str
    rca_category: RcaCategory
    rca_description: str
    rca_verified_by: str | None = None
    state: IncidentState = IncidentState.open
    severity: Severity = Severity.p2
    component: str = "unknown"
    first_signal_at: datetime | None = None
    rca_submitted_at: datetime | None = None
    mttr_seconds: int | None = None
    hash: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IncidentResult(BaseModel):
    status: int
    action: str
    incident: Incident | None = None
    reason: str | None = None
    errors: list[str] | None = None
