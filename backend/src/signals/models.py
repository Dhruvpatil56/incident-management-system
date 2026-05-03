from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from incident_pipeline.models import Severity


class Signal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    component_id: str
    component_type: str
    severity: Severity
    raw_payload: dict = Field(default_factory=dict)
    work_item_id: UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}
