from __future__ import annotations

import httpx

from incident_pipeline.models import Incident


class SlackAlert:
    def __init__(self, webhook_url: str | None):
        self.webhook_url = webhook_url

    async def send(self, incident: Incident) -> bool:
        if not self.webhook_url:
            return False
        payload = {
            "text": f"[{incident.severity.value}] {incident.title} ({incident.component})"
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(self.webhook_url, json=payload)
        return response.status_code < 300
