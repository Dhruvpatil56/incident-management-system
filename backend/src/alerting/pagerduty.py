from __future__ import annotations

import httpx

from incident_pipeline.models import Incident


class PagerDutyAlert:
    def __init__(self, routing_key: str | None, events_url: str):
        self.routing_key = routing_key
        self.events_url = events_url

    async def send(self, incident: Incident) -> bool:
        if not self.routing_key:
            return False
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": incident.title,
                "source": incident.source,
                "severity": "critical" if incident.severity.value == "P0" else "error",
                "custom_details": incident.model_dump(mode="json"),
            },
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(self.events_url, json=payload)
        return response.status_code < 300
