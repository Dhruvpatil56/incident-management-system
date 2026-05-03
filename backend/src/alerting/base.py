from __future__ import annotations

from typing import Protocol

from incident_pipeline.models import Incident


class AlertStrategy(Protocol):
    async def send(self, incident: Incident) -> bool:
        ...
